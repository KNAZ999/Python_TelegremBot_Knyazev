# knaz_tg_bot_calend/appointments/models.py

from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

# --- НОВЫЙ СПОСОБ ОБЪЯВЛЕНИЯ ---
UserModel = get_user_model()


# Это безопасно и всегда возвращает активную модель пользователя.
# --- КОНЕЦ НОВОГО СПОСОБА ---

class BotStatistics(models.Model):
    date = models.DateField(verbose_name="Дата", unique=True)
    user_count = models.PositiveIntegerField(default=0)
    event_count = models.PositiveIntegerField(default=0)
    edited_events = models.PositiveIntegerField(default=0)
    cancelled_events = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Статистика бота"
        verbose_name_plural = "Статистика бота"
        ordering = ['-date']

    def __str__(self):
        return f"Статистика за {self.date}"


class Event(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Активно'),
        (STATUS_CANCELLED, 'Отменено'),
    ]

    name = models.CharField("Название события", max_length=200)
    description = models.TextField("Описание", blank=True)

    # --- ИСПРАВЛЕННАЯ СТРОКА ---
    owner = models.ForeignKey(
        UserModel,  # <-- Используем переменную UserModel
        on_delete=models.CASCADE,
        verbose_name="Владелец события",
        related_name='events'
    )
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
    )
    is_public = models.BooleanField("Публичное событие", default=False)

    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"
        ordering = ['-created_at']
        db_table = 'events'

    def __str__(self):
        return self.name


# --- НОВАЯ МОДЕЛЬ ДЛЯ ВСТРЕЧ (ИЗ ЗАДАНИЯ №3) ---
class Appointment(models.Model):
    """
    Модель для хранения встреч между пользователями.
    """
    STATUS_PENDING = 'pending'  # Ожидание
    STATUS_CONFIRMED = 'confirmed'  # Подтверждено
    STATUS_CANCELLED = 'cancelled'  # Отменено

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидание'),
        (STATUS_CONFIRMED, 'Подтверждено'),
        (STATUS_CANCELLED, 'Отменено'),
    ]

    # Организатор встречи
    organizer = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name='organized_appointments',
        verbose_name='Организатор'
    )

    # Событие, на которое назначена встреча
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        verbose_name='Событие'
    )

    # Участники встречи (может быть много)
    participants = models.ManyToManyField(
        UserModel,
        related_name='participating_appointments',
        verbose_name='Участники'
    )

    date = models.DateField(verbose_name='Дата встречи')
    time = models.TimeField(verbose_name='Время встречи')
    details = models.TextField(verbose_name='Детали встречи', blank=True)

    status = models.CharField(
        verbose_name='Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    class Meta:
        verbose_name = 'Встреча'
        verbose_name_plural = 'Встречи'
        ordering = ['date', 'time']

    def __str__(self):
        return f"{self.organizer.username} - {self.event.name} - {self.date} {self.time} ({self.get_status_display()})"

    @classmethod
    def is_user_busy(cls, user, date, time):
        """
        Проверяет, свободен ли пользователь в указанное время.
        Возвращает True, если есть подтвержденная встреча.
        """
        return cls.objects.filter(
            participants=user,
            date=date,
            time=time,
            status=cls.STATUS_CONFIRMED
        ).exists()
# --- КОНЕЦ НОВОЙ МОДЕЛИ ---