import logging
from typing import Any

from ptbcontrib.roles import setup_roles
from sqlalchemy import Update
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application as PTBApplication, ApplicationBuilder, JobQueue, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.users.constants import RolesEnum
from app.core.users.repositories import UserRepository
from app.core.users.services import UserService
from app.handlers import HANDLERS
from app.infra.postgres.base import Base
from app.db import Database
from app.jobs.sync_roles import sync_roles
from appointments.models import BotStatistics
from settings.config import settings
import os
import django
from datetime import datetime
import pytz

# ЭТОТ БЛОК НУЖНО ДОБАВИТЬ
# Устанавливаем переменную окружения, указывающую на модуль настроек.
# 'knaz_tg_bot_calend' — это имя вашего главного каталога проекта,
# а 'settings' — это имя файла настроек (без .py).
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

# Теперь можно инициализировать Django
django.setup()



# Импорт модели статистики после настройки Django
# from events import BotStatistics


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


def update_statistics(field: str):
    """
    Обновляет счётчик в BotStatistics для текущей даты.
    Создаёт запись, если её нет.
    """
    stat, created = BotStatistics.objects.get_or_create(
        date=datetime.now().date(),
        defaults={
            'user_count': 0,
            'event_count': 0,
            'edited_events': 0,
            'cancelled_events': 0
        }
    )
    # Увеличиваем нужное поле
    if field == 'user_count':
        stat.user_count += 1
    elif field == 'event_count':
        stat.event_count += 1
    elif field == 'edited_events':
        stat.edited_events += 1
    elif field == 'cancelled_events':
        stat.cancelled_events += 1
    stat.save()


def configure_logging() -> None:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def create_app(app_settings: Any) -> Application:
    builder = ApplicationBuilder().application_class(Application)
    builder = builder.token(app_settings.API_TOKEN.get_secret_value())
    builder = builder.arbitrary_callback_data(True)
    builder = builder.post_init(Application.application_startup)
    builder = builder.post_shutdown(Application.application_shutdown)

    application: Application = builder.application_class(**builder._build_kwargs)

    scheduler = AsyncIOScheduler(timezone=pytz.UTC)
    job_queue = JobQueue(scheduler=scheduler)
    application._job_queue = job_queue
    application.job_queue.set_application(application)
    application.update_statistics = lambda field: update_statistics(field)

    return application


# --- Вставьте этот код в ваш app/main.py ---
# (лучше всего после других функций, но до блока if __name__ == '__main__')

async def invite_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для приглашения другого пользователя на встречу."""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Использование: /invite <имя_пользователя> <id_события>")
        return

    try:
        invited_username = args[0]
        event_id = int(args[1])

        user_id = context.user_data.get('django_user_id')
        if not user_id:
            await update.message.reply_text("Пожалуйста, войдите в систему.")
            return

        from appointments.models import Event, Appointment
        from django.contrib.auth import get_user_model

        UserModel = get_user_model()
        organizer = await UserModel.objects.aget(id=user_id)
        event = await Event.objects.aget(id=event_id, owner_id=user_id)

        try:
            invited_user = await UserModel.objects.aget(username=invited_username)

            if invited_user.id == organizer.id:
                await update.message.reply_text("Вы не можете пригласить самого себя.")
                return

            is_busy = await Appointment.is_user_busy(invited_user, event.date, event.time)
            if is_busy:
                await update.message.reply_text(f"Пользователь {invited_username} занят в это время.")
                return

            appointment = await Appointment.objects.acreate(
                organizer=organizer,
                event=event,
                date=event.date,
                time=event.time,
                status=Appointment.STATUS_PENDING
            )
            await appointment.participants.aadd(organizer, invited_user)

            await update.message.reply_text(f"Приглашение для {invited_username} отправлено! Статус: Ожидание.")

            # Уведомление приглашенного пользователя
            keyboard = [
                [
                    InlineKeyboardButton("✅ Подтвердить", callback_data=f"invite_accept_{appointment.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"invite_decline_{appointment.id}")
                ]
            ]
            markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=invited_user.telegram_id,
                text=f"Вас пригласили на встречу:\n{event.name}\n{event.date} {event.time}\nОрганизатор: {organizer.username}",
                reply_markup=markup
            )

        except UserModel.DoesNotExist:
            await update.message.reply_text(f"Пользователь с именем {invited_username} не найден.")

    except (Event.DoesNotExist, ValueError):
        await update.message.reply_text("Событие не найдено или указан неверный ID.")


async def handle_invite_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ответ на приглашение."""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split('_')

    if len(parts) < 3 or not parts[-1].isdigit():
        return

    action = parts[-2]
    appointment_id = int(parts[-1])

    try:
        from appointments.models import Appointment

        appointment = await Appointment.objects.aget(id=appointment_id)

        if action == "accept":
            appointment.status = Appointment.STATUS_CONFIRMED
            await appointment.asave()
            await query.edit_message_text("Встреча подтверждена!")

        elif action == "decline":
            appointment.status = Appointment.STATUS_CANCELLED
            await appointment.asave()
            await query.edit_message_text("Вы отклонили встречу.")

    except Appointment.DoesNotExist:
        await query.edit_message_text("Приглашение больше не действительно.")


# --- КОНЕЦ ВСТАВКИ ---

if __name__ == '__main__':
    configure_logging()
    app = create_app(settings)
    app.run()