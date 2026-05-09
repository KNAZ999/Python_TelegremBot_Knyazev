# app/api_views.py

import csv
import json
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from appointments.models import Event


@login_required
def export_events(request):
    """
    Конечная точка для выгрузки событий пользователя.
    Поддерживает форматы CSV и JSON.
    """
    # Определяем формат из GET-параметра (например, ?format=csv)
    format_type = request.GET.get('format', 'csv')

    # Получаем события ТОЛЬКО текущего авторизованного пользователя
    events = Event.objects.filter(owner=request.user)

    if format_type == 'csv':
        # --- ВЫГРУЗКА В CSV ---
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="calendar_events.csv"'

        writer = csv.writer(response)
        # Пишем заголовки столбцов
        writer.writerow(['Название', 'Дата', 'Время', 'Описание'])

        # Пишем данные для каждого события
        for event in events:
            writer.writerow([event.name, event.date, event.time, event.description])

        return response

    elif format_type == 'json':
        # --- ВЫГРУЗКА В JSON ---
        # Собираем данные в список словарей
        data = list(events.values('id', 'name', 'description', 'created_at', 'time'))

        response = HttpResponse(
            json.dumps(data, indent=4, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="calendar_events.json"'
        return response

    else:
        # Если формат не указан или неверный
        return HttpResponse("Неверный формат. Используйте ?format=csv или ?format=json", status=400)