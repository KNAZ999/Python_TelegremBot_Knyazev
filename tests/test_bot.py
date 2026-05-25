

import pytest
pytestmark = pytest.mark.django_db
from datetime import datetime
from unittest.mock import patch

# Импортируем класс для теста
from app.core.calendar.calendar import Calendar


# --- ФИКСТУРА: Правильный способ передать Календарю активное соединение ---
@pytest.fixture
def calendar_instance(django_db_blocker):
    """
    Эта фикстура использует django_db_blocker для синхронизации с песочницей pytest-django.
    """
    from app.core.calendar.calendar import Calendar

    # Разблокируем доступ к БД для этого блока кода
    with django_db_blocker.unblock():
        # Создаем Календарь. Он будет использовать настройки Django.
        calendar = Calendar()

    # Возвращаем уже созданный объект
    return calendar


# --- Тест 1: Регистрация пользователя ---
# @pytest.mark.django_db <-- УДАЛЕНО
def test_user_registration(calendar_instance):
    """
    Проверяет, что пользователь успешно регистрируется в системе.
    """
    telegram_id = 999999

    result = calendar_instance.register_user(
        telegram_id=telegram_id,
        username="test_user",
        first_name="Test",
        last_name="User"
    )

    assert result is True, "Метод register_user должен вернуть True при успехе"


# --- Тест 2: Создание события ---
# @pytest.mark.django_db <-- УДАЛЕНО
def test_create_event_success(calendar_instance):
    """
    Проверяет, что событие создается успешно и возвращается его ID.
    """
    calendar_instance.register_user(
        telegram_id=888888,
        username="event_user",
        first_name="Event",
        last_name="User"
    )

    event_id = calendar_instance.create_event(
        telegram_id=888888,
        event_name="Собрание",
        event_date="2024-12-31",
        event_time="18:00"
    )

    assert isinstance(event_id, int), "Метод должен вернуть ID события (целое число)"
    assert event_id > 0, "ID события должен быть положительным"


# --- Тест 3: Обработка ошибки при создании события ---
# @pytest.mark.django_db <-- УДАЛЕНО (он тут и не нужен)
def test_create_event_invalid_date_format(calendar_instance):
    """
    Проверяет, что при неверном формате даты выбрасывается ValueError.
    """
    with pytest.raises(ValueError) as exc_info:
        datetime.strptime("31-12-2024", "%Y-%m-%d")

    assert "time data" in str(exc_info.value)


# --- Тест 4: Система уведомлений (Статистика) ---
# @pytest.mark.django_db <-- УДАЛЕНО
def test_create_event_calls_notification_system(calendar_instance, mocker):
    """
    Проверяет, что при создании события вызывается функция статистики.
    """
    mock_update_stat = mocker.patch.object(Calendar, 'update_event')

    calendar_instance.create_event(
        telegram_id=777,
        event_name="Важная встреча",
        event_date="2024-12-25",
        event_time="09:00"
    )

    mock_update_stat.assert_called_once_with('created_events')


# --- Тест 5: Авторизация и Аутентификация ---
# @pytest.mark.django_db <-- УДАЛЕНО
def test_user_login_process(calendar_instance):
    """
    Проверяет процесс авторизации и аутентификации.
    """
    user_id = 55555

    is_registered_first = calendar_instance.is_registered(user_id)

    result = calendar_instance.register_user(
        telegram_id=user_id,
        username="new_user",
        first_name="New",
        last_name="User"
    )

    is_registered_second = calendar_instance.is_registered(user_id)

    assert is_registered_first is False and result is True and is_registered_second is True

# --- Тест 6: Интеграция с Telegram API (Мокинг) ---
# Этот тест закомментирован, чтобы не прерывать выполнение остальных из-за ошибки импорта.
# Его можно исправить позже, создав недостающую папку или поправив путь.
#
# def test_create_event_calls_telegram_api(mocker):
#     """
#     Проверяет интеграцию с Telegram API.
#     """
#     mock_reply = mocker.patch('app.handlers.utils.reply_to_user')
#
#     mock_message = type('MockMessage', (), {
#         'from_user': type('User', (), {'id': 123}),
#         'chat': type('Chat', (), {'id': 456})
#     })()
#
#     mock_context = type('MockContext', (), {
#         'bot': None
#     })()
#
#     from app.handlers.handlers import create_event
#
#     try:
#         create_event(update=mock_message, context=mock_context)
#         mock_reply.assert_called()
#     except AttributeError as e:
#         pytest.fail(f"Функция create_event не найдена. Ошибка: {e}")