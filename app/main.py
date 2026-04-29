import logging
from typing import Any

from ptbcontrib.postgres_persistence import PostgresPersistence
from ptbcontrib.roles import setup_roles, RolesHandler
from telegram.ext import Application as PTBApplication, ApplicationBuilder, JobQueue
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.users.constants import RolesEnum
from app.core.users.repositories import UserRepository
from app.core.users.services import UserService
from app.handlers import HANDLERS
from app.infra.postgres.base import Base
from app.db import Database
from app.jobs.sync_roles import sync_roles
from settings.config import settings

# Убедитесь, что используется pytz
import pytz


class Application(PTBApplication):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._roles = setup_roles(self)
        self.database = Database(dsn=settings.POSTGRES_DSN, base=Base)

        user_repository = UserRepository(session_factory=self.database._async_session)
        self.user_service = UserService(repository=user_repository)

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
    # Создаём Application без автоматического создания JobQueue
    builder = ApplicationBuilder().application_class(Application)
    builder = builder.token(app_settings.API_TOKEN.get_secret_value())
    builder = builder.arbitrary_callback_data(True)
    builder = builder.post_init(Application.application_startup)
    builder = builder.post_shutdown(Application.application_shutdown)

    # Важно: НЕ вызываем .build() сразу

    # Создаём Application
    application: Application = builder.application_class(**builder._build_kwargs)  # type: ignore

    # Вручную создаём JobQueue с правильным scheduler
    scheduler = AsyncIOScheduler(timezone=pytz.UTC)
    job_queue = JobQueue(scheduler=scheduler)
    application._job_queue = job_queue
    application.job_queue.set_application(application)

    return application


if __name__ == '__main__':
    configure_logging()
    app = create_app(settings)
    app.run()