# knaz_tg_bot_calend/appointments/admin.py

from django.contrib import admin
from .models import Event, BotStatistics # Импортируем обе модели

# Регистрация для Event (если еще не зарегистрирована)
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at', 'status', 'is_public')

# Регистрация для BotStatistics
@admin.register(BotStatistics)
class BotStatisticsAdmin(admin.ModelAdmin):
    list_display = ('date', 'user_count', 'event_count', 'edited_events', 'cancelled_events')