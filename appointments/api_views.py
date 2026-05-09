# appointments/api_views.py

from rest_framework import generics, permissions
from .models import Event
from .serializers import EventSerializer


class PublicEventListAPIView(generics.ListAPIView):
    """
    API для просмотра списка всех ПУБЛИЧНЫХ событий.
    Доступно всем (анонимным пользователям).
    """
    queryset = Event.objects.filter(is_public=True)
    serializer_class = EventSerializer


class MyEventsListCreateAPIView(generics.ListCreateAPIView):
    """
    API для просмотра и создания СОБСТВЕННЫХ событий.
    Требует, чтобы пользователь был авторизован.
    """
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]  # Защита: только для залогиненных

    def get_queryset(self):
        # Возвращаем только события текущего пользователя, который зашел по токену/авторизации
        return Event.objects.filter(owner=self.request.user)


from django.shortcuts import render

# Create your views here.
