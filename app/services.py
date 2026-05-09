# app/services.py

import datetime
from django.db.models import F
from appointments.models import BotStatistics


async def update_daily_stat(field_name: str):
    """
    Асинхронная функция для обновления статистики.
    field_name: название поля для инкремента (например, 'event_count', 'edited_events')
    """
    today = datetime.date.today()

    # Пробуем получить строку статистики за сегодня
    stat, created = await BotStatistics.objects.aget_or_create(
        date=today,
        defaults={
            'user_count': 0,
            'event_count': 0,
            'edited_events': 0,
            'cancelled_events': 0
        }
    )

    # Увеличиваем нужное поле на 1
    # Используем F() для безопасного обновления в базе данных
    await BotStatistics.objects.filter(pk=stat.pk).aupdate(
        **{field_name: F(field_name) + 1}
    )