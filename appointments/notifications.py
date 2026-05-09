from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from django.contrib.auth.models import User


# Предполагается, что у вас есть способ получить telegram_id по User
# Например, в профиле пользователя: user.profile.telegram_id


async def send_appointment_invitation(context: ContextTypes.DEFAULT_TYPE, appointment, participant):
    """
    Отправляет пользователю в Telegram приглашение на встречу с кнопками подтверждения.

    :param context: Контекст бота (Application)
    :param appointment: Объект Appointment
    :param participant: Объект User
    """
    # Получаем telegram_id участника
    try:
        telegram_id = participant.profile.telegram_id
        if not telegram_id:
            return False, "У участника не указан Telegram ID"
    except AttributeError:
        return False, "У пользователя нет профиля"

    # Текст сообщения
    message = (
        f"📨 *Приглашение на встречу*\n\n"
        f"Вы приглашены на событие:\n"
        f"*{appointment.event.name}*\n"
        f"📅 Дата: {appointment.date}\n"
        f"⏰ Время: {appointment.time}\n"
        f"Организатор: {appointment.organizer.username}"
    )

    # Кнопки: Подтвердить / Отклонить
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"accept_appointment_{appointment.id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_appointment_{appointment.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение
    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return True, "Приглашение отправлено"
    except Exception as e:
        return False, f"Ошибка при отправке: {str(e)}"