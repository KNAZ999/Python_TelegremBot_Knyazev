# appointments/serializers.py

from rest_framework import serializers
from .models import Event

class EventSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Event.
    Преобразует данные модели в JSON и обратно.
    """
    class Meta:
        model = Event
        # Укажи ПРАВИЛЬНЫЕ названия полей из твоей модели!
        # Если в модели нет полей 'date' и 'time', замени их!
        fields = ['id', 'name', 'description', 'created_at', 'updated_at', 'is_public', 'owner']