import os
import django
from django.conf import settings
from django.db import models, transaction
from django.contrib.auth import get_user_model
from sqlalchemy.exc import IntegrityError

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- ИНИЦИАЛИЗАЦИЯ DJANGO ---
# Этот блок должен быть в самом начале, чтобы избежать проблем с импортом моделей.
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knaz_tg_bot_calend.settings')
    django.setup()

# Импортируем модели после настройки Django
from appointments.models import Event, Appointment

UserModel = get_user_model()


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (HELPER FUNCTIONS) ---
# Вынесены для повторного использования и чистоты кода.

def _get_authenticated_user(context: ContextTypes.DEFAULT_TYPE):
    """Возвращает аутентифицированного пользователя или None."""
    user_id = context.user_data.get('django_user_id')
    if not user_id:
        return None
    try:
        return UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        return None


def _format_event_list(events_queryset):
    """Форматирует список событий в строку для ответа пользователю."""
    if not events_queryset.exists():
        return ["Ваш календарь пуст."]

    message_lines = []
    for event in events_queryset:
        status_emoji = "✅" if event.status == Event.STATUS_ACTIVE else "❌"
        line = (
            f"{status_emoji} <b>{event.name}</b>\n"
            f"ID: {event.id} | Дата: {event.date} {event.time}\n"
            f"Описание: {event.description[:50]}...\n"
            f"---"
        )
        message_lines.append(line)
    return message_lines


# --- КОМАНДЫ ТЕЛЕГРАМ-БОТА ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text(
        "Добро пожаловать! Используйте команду /login <ваш_id>, чтобы войти в свой календарь."
    )


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
    user = _get_authenticated_user(context)
    if not user:
        await update.message.reply_text("Пожалуйста, войдите в систему с помощью команды /login.")
        return

    # Личные события пользователя
    personal_events = await Event.objects.filter(owner=user).aall()

    message_lines = ["📅 Ваш личный календарь:"]
    message_lines.extend(_format_event_list(personal_events))

    # Публичные события других пользователей (Задание №5)
    public_events = await Event.objects.filter(is_public=True).exclude(owner=user).aall()

    if public_events:
        message_lines.append("\n🌍 Публичные события других пользователей:")
        for event in public_events:
            message_lines.append(f"🔓 <b>{event.name}</b> (владелец: {event.owner.username})")

    # Кнопка для скачивания CSV (Задание №6)
    download_button = InlineKeyboardButton(
        "⬇️ Скачать календарь (CSV)",
        url="http://127.0.0.1:8000/export/events/?format=csv"
    )
    reply_markup = InlineKeyboardMarkup([[download_button]])

    await update.message.reply_text("\n".join(message_lines), parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def create_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Создает новое событие для пользователя."""
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "Использование: /create <название> <дата(ГГГГ-ММ-ДД)> <время(ЧЧ:ММ)> [описание]"
        )
        return

    user = _get_authenticated_user(context)
    if not user:
        await update.message.reply_text("Пожалуйста, войдите в систему с помощью команды /login.")
        return

    name, date_str, time_str = args[0], args[1], args[2]
    description = " ".join(args[3:]) if len(args) > 3 else ""

    try:
        with transaction.atomic():
            event = await Event.objects.acreate(
                owner=user,
                name=name,
                date=date_str,
                time=time_str,
                description=description,
                status=Event.STATUS_ACTIVE,
                is_public=False,
            )
            # Обновляем статистику пользователя атомарно с созданием события
            user.events_created += 1
            await user.asave()

        await update.message.reply_text(
            f"✅ Событие '{name}' успешно создано на {date_str} в {time_str}."
        )

    except (ValueError, IntegrityError):
        await update.message.reply_text(
            "Ошибка при создании. Проверьте формат даты (ГГГГ-ММ-ДД) и времени (ЧЧ:ММ)."
        )


async def edit_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Редактирование или отмена события."""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Использование: /edit <id_события> <новое_название>")
        return

    user = _get_authenticated_user(context)
    if not user:
        await update.message.reply_text("Пожалуйста, войдите в систему.")
        return

    try:
        event_id = int(args[0])

        with transaction.atomic():
            event = await Event.objects.select_for_update().aget(id=event_id, owner=user)

            new_name = " ".join(args[1:])
            is_cancellation = new_name.lower() == "отмена"

            if is_cancellation:
                event.status = Event.STATUS_CANCELLED
                stat_field = 'cancelled_events'
            else:
                event.name = new_name
                stat_field = 'edited_events'
                user.events_edited += 1  # Статистика редактирования пользователя

            await event.asave()
            await user.asave()

            # Здесь вызывается функция статистики. Предполагается, что она асинхронная или не блокирующая.
            # Если она блокирующая, её нужно вызывать через run_in_executor.
            # update_daily_stat(stat_field)

        text = "отменено" if is_cancellation else "обновлено"
        await update.message.reply_text(f"Событие успешно {text}.")
# except (Event.DoesNotExist, ValueError) as e: # type: ignore[assignment]
#     await update.message.reply_text("Событие не найдено или у вас нет прав на его редактирование.")


async def share_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Делает событие пользователя публичным."""
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /share <id_события>")
        return

    user = _get_authenticated_user(context)
    if not user:
        await update.message.reply_text("Пожалуйста, войдите в систему.")
        return

    try:
        event_id = int(args[0])
        event = await Event.objects.aget(id=event_id, owner=user)

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

    invited_username, event_id_str = args[0], args[1]
    organizer = _get_authenticated_user(context)

    if not organizer:
        await update.message.reply_text("Пожалуйста, войдите в систему.")
        return

    try:
        event_id = int(event_id_str)
        invited_user = await UserModel.objects.aget(username=invited_username)

        if invited_user.id == organizer.id:
            await update.message.reply_text("Вы не можете пригласить самого себя.")
            return

        event = await Event.objects.aget(id=event_id, owner=organizer)

        # Проверка занятости приглашаемого пользователя (добавлена логика в модель)
        is_busy = await Appointment.is_user_busy(invited_user, event.date, event.time)
        if is_busy:
            await update.message.reply_text(f"Пользователь {invited_username} занят в это время.")
            return

        # Создаем встречу (Appointment)
        appointment = await Appointment.objects.acreate(
            organizer=organizer,
            event=event,
            date=event.date,
            time=event.time,
            status=Appointment.STATUS_PENDING,
        )
        # Добавляем участников. В Django ManyToMany через .add() требует сохранения объекта.
        appointment.participants.add(organizer, invited_user)

        # Уведомление организатору
        await update.message.reply_text(f"Приглашение для {invited_username} отправлено! Статус: Ожидание.")

        # Уведомление приглашенному пользователю через Telegram
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
    if not query:
        return
    await query.answer()

    data = query.data
    action_mapper = {
        'invite_accept_': ('Принято', Appointment.STATUS_CONFIRMED),
        'invite_decline_': ('Отклонено', Appointment.STATUS_CANCELLED),
    }

    for prefix, (text_response, new_status) in action_mapper.items():
        if data.startswith(prefix):
            try:
                appointment_id = int(data.replace(prefix, ''))
                appointment = await Appointment.objects.aget(id=appointment_id)

                appointment.status = new_status
                await appointment.asave()

                await query.edit_message_text(f"Встреча {text_response.lower()}!")

            except Appointment.DoesNotExist:
                await query.edit_message_text("Приглашение больше не действительно.")
            break  # Выходим из цикла после обработки