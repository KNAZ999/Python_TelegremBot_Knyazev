# appointments/api_urls.py

from django.urls import path
from .api_views import PublicEventListAPIView, MyEventsListCreateAPIView

urlpatterns = [
    path('public/', PublicEventListAPIView.as_view(), name='api-events-public'),
    path('my/', MyEventsListCreateAPIView.as_view(), name='api-events-my'),
]