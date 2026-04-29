import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime


class Calendar:
    def __init__(self, db_config):
        self.db_config = db_config
        self._create_tables()

    def _get_connection(self):
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)

    def _create_tables(self):
        """Создаёт таблицы, если их нет"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # Выполняется через SQL выше, но можно оставить на всякий
            pass
        except Exception as e:
            print(f"Ошибка при создании таблиц: {e}")
        finally:
            if conn:
                conn.close()

    def register_user(self, telegram_id: int, username: str, first_name: str, last_name: str):
        """Регистрирует пользователя"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name
                RETURNING id;
            """, (telegram_id, username, first_name, last_name))
            conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка регистрации: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def is_registered(self, telegram_id: int) -> bool:
        """Проверяет, зарегистрирован ли пользователь"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE telegram_id = %s", (telegram_id,))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Ошибка проверки регистрации: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def create_event(self, telegram_id: int, event_name: str, event_date: str, event_time: str, event_details: str = ""):
        """Создаёт событие для пользователя"""
        try:
            datetime.strptime(event_date, "%Y-%m-%d")
            datetime.strptime(event_time, "%H:%M")
        except ValueError:
            raise ValueError("Неверный формат даты (ГГГГ-ММ-ДД) или времени (ЧЧ:ММ)")

        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (user_id, name, date, time, details)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """, (telegram_id, event_name.strip(), event_date, event_time, event_details.strip() or "Без описания"))
            event_id = cursor.fetchone()["id"]
            conn.commit()
            return event_id
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def get_user_events(self, telegram_id: int):
        """Возвращает все события пользователя"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM events 
                WHERE user_id = %s 
                ORDER BY date, time;
            """, (telegram_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Ошибка получения событий: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_event(self, event_id: int, telegram_id: int):
        """Получает событие, только если оно принадлежит пользователю"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM events 
                WHERE id = %s AND user_id = %s;
            """, (event_id, telegram_id))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"Ошибка: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def update_event(self, event_id: int, telegram_id: int, **updates):
        """Обновляет событие, если оно принадлежит пользователю"""
        allowed_fields = {'name', 'date', 'time', 'details'}
        set_parts = []
        params = []

        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                if field == 'date':
                    datetime.strptime(value, "%Y-%m-%d")
                if field == 'time':
                    datetime.strptime(value, "%H:%M")
                set_parts.append(f"{field} = %s")
                params.append(value.strip() if isinstance(value, str) else value)

        if not set_parts:
            return True

        params.append(event_id)
        params.append(telegram_id)

        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = f"UPDATE events SET {', '.join(set_parts)} WHERE id = %s AND user_id = %s;"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def delete_event(self, event_id: int, telegram_id: int) -> bool:
        """Удаляет событие, только если оно принадлежит пользователю"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE id = %s AND user_id = %s;", (event_id, telegram_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Ошибка удаления: {e}")
            return False
        finally:
            if conn:
                conn.close()