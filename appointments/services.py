from datetime import date
from django.db import transaction
from .models import Appointment
from .utils import get_user_busy_intervals


@transaction.atomic
def invite_participant_to_appointment(appointment, participant):
    """
    Приглашает участника на встречу.
    Проверяет, свободен ли он в указанное время и дату.

    :param appointment: Объект Appointment
    :param participant: Объект User (пользователь-участник)
    :return: (успех: bool, сообщение: str)
    """
    # Получаем занятые интервалы участника на дату встречи
    busy_intervals = get_user_busy_intervals(participant, appointment.date)
    appointment_time_str = appointment.time.strftime('%H:%M')

    # Проверяем, не пересекается ли время встречи с занятыми интервалами
    for start, end in busy_intervals:
        if start <= appointment_time_str < end:
            return False, f"Участник {participant.username} занят в это время."

    # Добавляем участника к встрече
    appointment.participants.add(participant)

    # Если это первый участник, можно изменить статус на "ожидание"
    if appointment.status == 'pending':
        # Статус остаётся 'pending', так как ожидаем подтверждения
        pass

    return True, f"Участник {participant.username} приглашён. Ожидание подтверждения."