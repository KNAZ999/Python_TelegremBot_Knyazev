from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

# Создаем новый класс админки, наследуясь от встроенного UserAdmin
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Админ-панель для кастомной модели пользователя.
    """
    # Поля, которые будут отображаться в списке пользователей
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'is_staff', 'telegram_id',
        'events_created', 'events_edited', 'events_cancelled'
    )

    # Поля, по которым можно искать
    search_fields = ('username', 'email', 'telegram_id')

    # Эти поля можно добавить в форму создания/редактирования, если нужно
    # fieldsets = UserAdmin.fieldsets + (
    #     (None, {'fields': ('telegram_id',)}),
    # )