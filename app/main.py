import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application as PTBApplication, ExtBot, ContextTypes, JobQueue, Updater
from app.core.users.constants import RolesEnum
from app.core.users.repositories import UserRepository
from app.core.users.services import UserService
from app.handlers import HANDLERS
from app.infra.postgres.base import Base
from app.infra.postgres.db import Database
from app.jobs.sync_roles import sync_roles
from settings.config import settings

# Импортируем pytz — обязательно для совместимости с APScheduler
import pytz


# Простая реализация ролей без ptbcontrib.roles
class RoleManager:
    def __init__(self):
        self._roles = {}

    def add_role(self, role_name: str):
        if role_name not in self._roles:
            self._roles[role_name] = set()

    def add_user_ids(self, role_name: str, *user_ids: int):
        if role_name not in self._roles:
            self.add_role(role_name)
        self._roles[role_name].update(user_ids)

    def has_user(self, role_name: str, user_id: int) -> bool:
        return user_id in self._roles.get(role_name, set())

    def get_users(self, role_name: str) -> set[int]:
        return self._roles.get(role_name, set())

    def __getitem__(self, item):
        return self._roles[item]

    def __contains__(self, item):
        return item in self._roles


def setup_roles(app):
    app._roles = RoleManager()
    return app._roles


class Application(PTBApplication):
    def __init__(self, **kwargs: Any) -> None:
        # Извлекаем нужные параметры
        token = kwargs.pop('token', None)
        if not token:
            raise ValueError("Token is required")

        arbitrary_callback_data = kwargs.pop('arbitrary_callback_data', False)
        post_init = kwargs.pop('post_init', None)
        post_shutdown = kwargs.pop('post_shutdown', None)
        post_stop = kwargs.pop('post_stop', None)

        # Удаляем неподдерживаемые параметры
        kwargs.pop('context', None)

        # Создаём bot вручную
        bot = ExtBot(token=token)

        # Создаём updater
        updater = Updater(bot=bot, update_queue=None)

        # Создаём context_types
        context_types = ContextTypes()

        # Создаём scheduler с pytz.UTC
        scheduler = AsyncIOScheduler(timezone=pytz.UTC)

        # Создаём пустой экземпляр JobQueue без вызова __init__
        job_queue = object.__new__(JobQueue)

        # Устанавливаем только те поля, которые используются при старте
        # Не устанавливаем _running, _application и другие — они будут установлены при .start()
        job_queue.scheduler = scheduler  # ← это свойство с setter'ом — безопасно

        # Передаём всё в super()
        super().__init__(
            bot=bot,
            update_queue=None,
            updater=updater,
            job_queue=job_queue,
            update_processor=None,
            persistence=None,
            context_types=context_types,
            post_init=post_init,
            post_shutdown=post_shutdown,
            post_stop=post_stop,
            **kwargs
        )

        # Настраиваем остальное
        self._roles = setup_roles(self)
        self.database = Database(dsn=settings.POSTGRES_DSN, base=Base)

        # Передаём весь экземпляр database
        user_repository = UserRepository(database=self.database)
        self.user_service = UserService(repository=user_repository)

        # Вручную устанавливаем arbitrary_callback_data
        self.arbitrary_callback_data = arbitrary_callback_data

    @staticmethod
    async def application_startup(application: "Application") -> None:
        await application.database.create_tables()
        await application.setup_roles()
        application.register_handlers()
        application.setup_jobs()

    @staticmethod
    async def application_shutdown(application: "Application") -> None:
        await application.database.shutdown()

    def run(self) -> None:
        self.run_polling()

    def register_handlers(self) -> None:
        for handler in HANDLERS:
            if handler.role:
                if self._roles is None:
                    raise Exception("Roles are not set up")
                role_handler = self._roles[handler.role]
                role_handler.add_handler(handler.handler)
            else:
                self.add_handler(handler.handler)

    async def setup_roles(self) -> None:
        for role in RolesEnum:
            if role.value not in self._roles:
                self._roles.add_role(role.value)

            user_ids = await self.user_service.get_user_ids_for_role(role.value)
            if user_ids:
                self._roles[role.value].add_user_ids(*user_ids)

    def setup_jobs(self) -> None:
        if self.job_queue is None:
            raise Exception("Job queue missing")
        self.job_queue.run_repeating(
            callback=sync_roles,
            interval=60,
            first=10
        )


def configure_logging() -> None:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def create_app(app_settings: Any) -> Application:
    # Создаём Application напрямую
    application = Application(
        token=app_settings.API_TOKEN.get_secret_value(),
        arbitrary_callback_data=True,
        post_init=Application.application_startup,
        post_shutdown=Application.application_shutdown,
    )

    return application


if __name__ == '__main__':
    configure_logging()
    app = create_app(settings)
    app.run()