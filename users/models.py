# knaz_tg_bot_calend/users/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class CustomUser(AbstractUser):
    """
    Кастомная модель пользователя, расширяющая стандартную.
    """
    # Поле для хранения ID из Telegram
    telegram_id = models.BigIntegerField(
        "ID в Telegram",
        unique=True,  # ID должен быть уникальным для каждого пользователя
        null=True,
        blank=True
    )

    # Счетчики для статистики (из Задания №4)
    events_created = models.PositiveIntegerField("Создано событий", default=0)
    events_edited = models.PositiveIntegerField("Отредактировано событий", default=0)
    events_cancelled = models.PositiveIntegerField("Отменено событий", default=0)

    def __str__(self):
        # Отображает имя пользователя или его ID, если имени нет
        return self.username or f"User_{self.telegram_id}"

    # --- ДОБАВЬТЕ ЭТОТ БЛОК META ---
    class Meta:
        # Говорим Django использовать таблицу с именем 'users'
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'