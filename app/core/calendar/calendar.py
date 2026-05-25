import logging
from datetime import datetime
from django.conf import settings
import psycopg2
from psycopg2.extras import RealDictCursor

# Настройка логгера (вместо print)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Calendar:
    def __init__(self, db_config=None):
        self.db_config = db_config

    def _get_connection(self):
        """Получает новое подключение к БД из настроек Django."""
        try:
            db_settings = settings.DATABASES['default']
            return psycopg2.connect(
                dbname=db_settings['NAME'],
                user=db_settings['USER'],
                password=db_settings['PASSWORD'],
                host=db_settings['HOST'],
                port=db_settings['PORT'],
                cursor_factory=RealDictCursor
            )
        except Exception as e:
            logger.error(f"Не удалось подключиться к БД: {e}")
            raise

    def _execute(self, query, params=(), fetch=False, fetch_all=False, return_id=False):
        """
        Главный метод для выполнения запросов.
        Устраняет дублирование кода для подключения, коммита и закрытия БД.
        """
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:  # Используем контекстный менеджер для курсора
                cursor.execute(query, params)

                if fetch:
                    return cursor.fetchone()
                if fetch_all:
                    return cursor.fetchall()
                if return_id:
                    row = cursor.fetchone()
                    conn.commit()
                    return row['id'] if row else None

                # Для UPDATE, INSERT (без returning), DELETE
                conn.commit()
                return True

        except Exception as e:
            if conn:
                conn.rollback()
            raise e  # Перебрасываем ошибку, чтобы её обработал внешний блок
        finally:
            if conn:
                conn.close()  # Закрываем соединение

    def register_user(self, telegram_id: int, username: str, first_name: str, last_name: str):
        """Регистрирует пользователя в таблице users"""
        query = """
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name;
        """
        params = (telegram_id, username, first_name, last_name)
        try:
            self._execute(query, params)
            return True
        except Exception as e:
            logger.error(f"Ошибка регистрации: {e}")
            return False

    def is_registered(self, telegram_id: int) -> bool:
        """Проверяет, зарегистрирован ли пользователь"""
        query = "SELECT 1 FROM users WHERE telegram_id = %s"
        result = self._execute(query, (telegram_id,), fetch=True)
        return result is not None

    def create_event(self, telegram_id: int, event_name: str, event_date: str, event_time: str,
                     event_details: str = ""):
        """Создаёт событие для пользователя в таблице events."""
        # Валидация дат (может выбросить ValueError)
        datetime.strptime(event_date, "%Y-%m-%d")
        datetime.strptime(event_time, "%H:%M")

        query = """
            INSERT INTO events (owner_id, name, created_at, time, details)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """
        params = (telegram_id, event_name.strip(), event_date, event_time,
                  event_details.strip() or "Без описания")

        return self._execute(query, params, return_id=True)

    def get_user_events(self, telegram_id: int):
        """Возвращает все события пользователя"""
        query = "SELECT * FROM events WHERE owner_id = %s ORDER BY created_at;"
        rows = self._execute(query, (telegram_id,), fetch_all=True) or []
        return [dict(row) for row in rows]

    def get_event(self, event_id: int, telegram_id: int):
        """Получает событие по ID и владельцу"""
        query = "SELECT * FROM events WHERE id = %s AND owner_id = %s;"
        row = self._execute(query, (event_id, telegram_id), fetch=True)
        return dict(row) if row else None

    def update_event(self, event_id: int, telegram_id: int, **updates):
        """Обновляет событие"""
        allowed_fields = {'name', 'created_at', 'time', 'details'}
        set_parts = [f"{f} = %s" for f in updates if f in allowed_fields]
        params = [updates[f] for f in updates if f in allowed_fields]

        if not set_parts:
            raise ValueError("Нет полей для обновления")  # Явная ошибка вместо True

        params.extend([event_id, telegram_id])

        query = f"UPDATE events SET {', '.join(set_parts)} WHERE id = %s AND owner_id = %s;"
        self._execute(query, tuple(params))
        return True

    def delete_event(self, event_id: int, telegram_id: int) -> bool:
        """Удаляет событие"""
        query = "DELETE FROM events WHERE id = %s AND owner_id = %s;"
        self._execute(query, (event_id, telegram_id))
        return True