from telegram import Update
from telegram.ext import ContextTypes
from appointments.models import Appointment


async def handle_appointment_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик нажатия на кнопки "Подтвердить" / "Отклонить" встречу.
    Обновляет статус встречи в зависимости от выбора.
    """
    query = update.callback_query
    await query.answer()

    # Данные из callback_data: например, "accept_appointment_123" или "decline_appointment_123"
    data = query.data
    user = query.from_user

    try:
        if data.startswith("accept_appointment_"):
            appointment_id = int(data.split("_")[-1])
            appointment = Appointment.objects.get(id=appointment_id)

            # Проверяем, что пользователь — участник
            if user.id in appointment.participants.values_list('profile__telegram_id', flat=True):
                appointment.status = 'confirmed'
                appointment.save()
                await query.edit_message_text(text="✅ Вы подтвердили встречу.")
                await notify_organizer(appointment, f"Участник @{user.username} подтвердил встречу.")
            else:
                await query.answer("Вы не приглашены на эту встречу.", show_alert=True)

        elif data.startswith("decline_appointment_"):
            appointment_id = int(data.split("_")[-1])
            appointment = Appointment.objects.get(id=appointment_id)

            if user.id in appointment.participants.values_list('profile__telegram_id', flat=True):
                appointment.status = 'cancelled'
                appointment.save()
                await query.edit_message_text(text="❌ Вы отклонили встречу.")
                await notify_organizer(appointment, f"Участник @{user.username} отклонил встречу.")
            else:
                await query.answer("Вы не приглашены на эту встречу.", show_alert=True)

    except Appointment.DoesNotExist:
        await query.edit_message_text(text="❌ Встреча не найдена.")
    except Exception as e:
        await query.edit_message_text(text=f"Ошибка: {str(e)}")


async def notify_organizer(appointment: Appointment, message: str):
    """
    Отправляет уведомление организатору встречи.
    """
    try:
        bot = appointment.organizer.profile.telegram_id
        await appointment.organizer.application.bot.send_message(
            chat_id=bot,
            text=message
        )
    except Exception as e:
        # Логируем ошибку, если не удалось отправить
        print(f"Не удалось уведомить организатора: {e}")