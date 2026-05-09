"""
URL configuration for knaz_t_g_bot_calend project.
"""
from django.contrib import admin
from django.urls import path, include  # <-- ИМПОРТ include отсюда!
from app import views  # <-- ИМПОРТ views отсюда!

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- НОВАЯ СТРОКА ДЛЯ ВЫГРУЗКИ ---
    path('export/events/', views.export_events, name='export_events'),

    # --- НОВАЯ СТРОКА ДЛЯ API ---
    path('api/', include('appointments.api_urls')),
    # ---------------------------------
]