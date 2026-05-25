from django.urls import path
from . import api_views

urlpatterns = [
    path('public/', api_views.PublicEventListAPIView.as_view(), name='api-events-public'),
    path('my/', api_views.MyEventsListCreateAPIView.as_view(), name='api-events-my'),
]