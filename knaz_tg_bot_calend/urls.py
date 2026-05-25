"""
URL configuration for knaz_tg_bot_calend project.
"""
from django.contrib import admin
from django.urls import path, include  # <-- ИМПОРТ include отсюда!
from app import views  # <-- ИМПОРТ views отсюда!
from django.urls import path
from app import views # Убедись, что этот импорт есть

urlpatterns = [
    # --- ИЗМЕНЕННЫЙ БЛОК ДЛЯ АДМИНКИ ---
    # Grappelli должен быть первым, чтобы его стили и URL работали
    path('admin/', include('grappelli.urls')),
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    # ------------------------------------

    # --- НОВАЯ СТРОКА ДЛЯ ВЫГРУЗКИ ---
    path('export/events/', views.export_events, name='export_events'),

    # --- НОВАЯ СТРОКА ДЛЯ API ---
    path('api/', include('appointments.api_urls')),
    # ---------------------------------
]