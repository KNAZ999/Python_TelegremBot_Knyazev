# app/handlers.py

from django.db import models, transaction
from django.conf import settings
from django.contrib.auth import get_user_model
from app.core.orders.constants import OrderStatusEnum
from app.core.orders.exceptions import ActiveOrderExists
from app.core.orders.services import OrderService, ProductService
from app.core.users.services import UserService
from app.handlers import HANDLERS
from app.handlers.helpers import build_order_buttons, format_order_contents, format_order_contents_for_waiter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CallbackQueryHandler
from app.services import update_daily_stat  # Импорт функции для статистики
from appointments.models import Event, Appointment  # Импортируем и Event, и Appointment

UserModel = get_user_model()


# --- СТАРТОВЫЕ И ЗАКАЗЫ (ИЗ ПЕРВОЙ ЧАСТИ ПРОЕКТА) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start.
    Приветствует пользователя.
    """
    await update.message.reply_text(
        "Добро пожаловать! Используйте команду /login <ваш_id>, чтобы войти в свой календарь."
    )


async def create_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (ваш код для заказов) ...
    # Этот блок можно оставить, если функционал заказов нужен,
    # или удалить, если вы фокусируетесь только на календаре.
    pass


# ... остальные функции для заказов (add_item, finish_order) ...
# Если они не используются в основном сценарии календаря, их можно закомментировать или удалить.


# --- КАЛЕНДАРЬ И ВСТРЕЧИ (ИЗ ВТОРОЙ ЧАСТИ ПРОЕКТА) ---

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Вход пользователя по Telegram ID."""
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /login <ваш_telegram_id>")
        return

    try:
        telegram_id = int(args[0])
        user = await UserModel.objects.aget(telegram_id=telegram_id)
        context.user_data['django_user_id'] = user.id
        await update.message.reply_text(f"Вы успешно вошли как {user.username}.")
    except (UserModel.DoesNotExist, ValueError):
        await update.message.reply_text("Пользователь не найден или неверный ID.")


async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает календарь пользователя и общие события."""
    user_id = context.user_data.get('django_user_id')

    if not user_id:
        await update.message.reply_text("Пожалуйста, войдите в систему с помощью команды /login.")
        return

    events = await Event.objects.filter(owner_id=user_id)

    message_lines = ["📅 Ваш личный календарь:"]

    if events:
        for event in events:
            status_emoji = "✅" if event.status == Event.STATUS_ACTIVE else "❌"
            line = (
                f"{status_emoji} <b>{event.name}</b>\n"
                f"ID: {event.id} | Создано: {event.created_at.date()}\n"
                f"Описание: {event.description[:50]}...\n"
                f"---"
            )
            message_lines.append(line)
    else:
        message_lines.append("Ваш календарь пуст.")

    # --- НОВЫЙ КОД ДЛЯ ВЫГРУЗКИ (ЗАДАНИЕ №6) ---
    # Кнопка для скачивания CSV-файла
    download_button = InlineKeyboardButton(
        "⬇️ Скачать календарь (CSV)",
        url="http://127.0.0.1:8000/export/events/?format=csv"
    )
    reply_markup = InlineKeyboardMarkup([[download_button]])
    # --- КОНЕЦ НОВОГО КОДА ---

    # --- НОВЫЙ КОД ДЛЯ ПУБЛИЧНЫХ СОБЫТИЙ (ЗАДАНИЕ №5) ---
    public_events = await Event.objects.filter(is_public=True).exclude(owner_id=user_id)

    if public_events.exists():
        message_lines.append("\n🌍 Публичные события других пользователей:")
        for event in public_events:
            message_lines.append(f"🔓 <b>{event.name}</b> (владелец: {event.owner.username})")
    # --- КОНЕЦ НОВОГО КОДА ---

    await update.message.reply_text("\n".join(message_lines), parse_mode='HTML', reply_markup=reply_markup)


async def edit_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Редактирование или отмена события."""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Использование: /edit <id_события> <новое_название>")
        return

    try:
        event_id = int(args[0])
        new_name = " ".join(args[1:])

        user_id = context.user_data.get('django_user_id')
        if not user_id:
            await update.message.reply_text("Пожалуйста, войдите в систему.")
            return

        event = await Event.objects.aget(id=event_id, owner_id=user_id)

        # Логика отмены: если новое название "отмена"
        is_cancellation = new_name.lower() == "отмена"

        with transaction.atomic():
            if is_cancellation:
                event.status = Event.STATUS_CANCELLED
                stat_field = 'cancelled_events'
            else:
                event.name = new_name
                event.owner.events_edited += 1
                await event.owner.asave()
                stat_field = 'edited_events'

            await event.asave()
            await update_daily_stat(stat_field)

        text = "отменено" if is_cancellation else "обновлено"
        await update.message.reply_text(f"Событие успешно {text}.")

    except (Event.DoesNotExist, ValueError):
        await update.message.reply_text("Событие не найдено или у вас нет прав на его редактирование.")


async def share_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Делает событие пользователя публичным."""
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /share <id_события>")
        return

    try:
        event_id = int(args[0])

        user_id = context.user_data.get('django_user_id')
        if not user_id:
            await update.message.reply_text("Пожалуйста, войдите в систему.")
            return

        event = await Event.objects.aget(id=event_id, owner_id=user_id)

        event.is_public = True
        await event.asave()

        await update.message.reply_text(f"Событие '{event.name}' теперь является публичным.")

    except (Event.DoesNotExist, ValueError):
        await update.message.reply_text("Событие не найдено или у вас нет прав на него.")


# --- НОВЫЙ КОД ДЛЯ ЗАДАНИЯ №3 (ВСТРЕЧИ) ---
async def invite_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для приглашения другого пользователя на встречу."""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Использование: /invite <имя_пользователя> <id_события>")
        return

    try:
        invited_username, event_id = args[0], int(args[1])

        user_id = context.user_data.get('django_user_id')
        if not user_id:
            await update.message.reply_text("Пожалуйста, войдите в систему.")
            return

        organizer = await UserModel.objects.aget(id=user_id)
        event = await Event.objects.aget(id=event_id, owner_id=user_id)

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

        if invited_user.telegram_id:
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
                reply_markup=markup,
            )

    except (UserModel.DoesNotExist, Event.DoesNotExist, ValueError):
        await update.message.reply_text("Пользователь или событие не найдены.")


async def handle_invite_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ответ на приглашение."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith('invite_accept_'):
        action = 'accept'
        appointment_id = int(data.replace('invite_accept_', ''))
    elif data.startswith('invite_decline_'):
        action = 'decline'
        appointment_id = int(data.replace('invite_decline_', ''))
    else:
        return

    try:
        appointment = await Appointment.objects.aget(id=appointment_id)

        if action == 'accept':
            appointment.status = Appointment.STATUS_CONFIRMED
            text_response = "Встреча подтверждена!"

        elif action == 'decline':
            appointment.status = Appointment.STATUS_CANCELLED
            text_response = "Вы отклонили встречу."

        await appointment.asave()

        await query.edit_message_text(text_response)

    except Appointment.DoesNotExist:
        await query.edit_message_text("Приглашение больше не действительно.")
# --- КОНЕЦ НОВОГО КОДА ДЛЯ ВСТРЕЧЕЙ ---

# --- РЕГИСТРАЦИЯ НОВЫХ КОМАНД В СПИСОК HANDLERS ---
from telegram.ext import CommandHandler

HANDLERS.extend([
     CommandHandler('calendar', calendar),
     CommandHandler('share', share_event),
     CommandHandler('invite', invite_user),
     CallbackQueryHandler(handle_invite_response, pattern="^invite_"),
 ])