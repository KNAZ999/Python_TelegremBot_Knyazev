from datetime import date, time
from .models import Appointment


def get_user_busy_intervals(user, target_date: date):
    """
    Возвращает список занятых временных интервалов пользователя на указанную дату.

    :param user: Пользователь (объект User)
    :param target_date: Дата для проверки
    :return: Список кортежей (время начала, время окончания), например [('10:00', '11:00')]
             Сейчас считаем, что встреча длится 1 час (можно расширить).
    """
    # Получаем все встречи, где пользователь — участник или организатор, и статус не "отменён"
    appointments = Appointment.objects.filter(
        participants=user,
        date=target_date,
        status__in=['confirmed', 'pending']
    ).values_list('time', flat=True)

    # Предположим, каждая встреча длится 1 час
    busy_intervals = []
    for start_time in appointments:
        # Простой способ: конец = начало + 1 час
        if isinstance(start_time, str):
            start_time = start_time.split(":")[0] + ":00"  # нормализуем
        # В реальном проекте можно добавить поле duration
        busy_intervals.append((str(start_time), _add_one_hour(str(start_time))))

    return busy_intervals


def _add_one_hour(time_str: str) -> str:
    """Вспомогательная функция: добавляет 1 час к строке времени"""
    hour = int(time_str.split(":")[0])
    return f"{(hour + 1) % 24:02d}:00"