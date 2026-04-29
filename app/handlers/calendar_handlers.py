# from telegram import Update
# from telegram.ext import CallbackContext
# from app.core.calendar.calendar import Calendar
# from app.secrets import DB_CONFIG
# from app.core.calendar.calendar import Calendar
#
# # === Глобальный экземпляр календаря с подключением к БД ===
# try:
#     calendar = Calendar(DB_CONFIG)
#     print("✅ Подключение к PostgreSQL установлено.")
# except Exception as e:
#     print(f"❌ Не удалось подключиться к базе данных: {e}")
#     calendar = None
#
# def register_handler(update: Update, context: CallbackContext):
#     """Регистрация пользователя"""
#     user = update.effective_user
#     telegram_id = user.id
#     username = user.username
#     first_name = user.first_name
#     last_name = user.last_name
#
#     if calendar.is_registered(telegram_id):
#         update.message.reply_text("✅ Вы уже зарегистрированы!")
#         return
#
#     success = calendar.register_user(telegram_id, username, first_name, last_name)
#     if success:
#         update.message.reply_text(
#             f"🎉 Добро пожаловать, {first_name}!\n"
#             "Вы успешно зарегистрированы в календаре."
#         )
#     else:
#         update.message.reply_text("❌ Ошибка регистрации. Попробуйте позже.")
#
#
# def create_event_start(update: Update, context: CallbackContext):
#     """Начало создания события"""
#     telegram_id = update.effective_user.id
#
#     if not calendar.is_registered(telegram_id):
#         update.message.reply_text("❌ Сначала зарегистрируйтесь: /register")
#         return
#
#     context.user_data['awaiting'] = 'event_data'
#     update.message.reply_text(
#         "📝 Введите данные события в формате:\n"
#         "`Название | Дата (ГГГГ-ММ-ДД) | Время (ЧЧ:ММ) | Описание`",
#         parse_mode="Markdown"
#     )
#
# def handle_message(update: Update, context: CallbackContext):
#     """Обрабатывает ввод после команд"""
#     text = update.message.text
#     telegram_id = update.effective_user.id
#
#     if context.user_data.get('awaiting') == 'event_data':
#         context.user_data.pop('awaiting')
#
#         try:
#             parts = text.split(" | ")
#             if len(parts) < 3:
#                 update.message.reply_text("❌ Неверный формат. Пример:\n`Название | 2025-04-10 | 14:30 | Встреча`", parse_mode="Markdown")
#                 return
#
#             name = parts[0].strip()
#             date = parts[1].strip()
#             time = parts[2].strip()
#             details = parts[3].strip() if len(parts) > 3 else ""
#
#             event_id = calendar.create_event(telegram_id, name, date, time, details)
#             update.message.reply_text(f"✅ Событие *'{name}'* создано! ID: `{event_id}`", parse_mode="Markdown")
#
#         except ValueError as e:
#             update.message.reply_text(f"❌ Ошибка: {e}")
#         except Exception as e:
#             update.message.reply_text("❌ Не удалось создать событие.")
#         return
#
#     # Дефолтное сообщение
#     update.message.reply_text("Используйте команды: /help")
#
# def list_my_events(update: Update, context: CallbackContext):
#     telegram_id = update.effective_user.id
#     if not calendar.is_registered(telegram_id):
#         update.message.reply_text("❌ Зарегистрируйтесь: /register")
#         return
#
#     events = calendar.get_user_events(telegram_id)
#     if not events:
#         update.message.reply_text("🗓 У вас пока нет событий.")
#         return
#
#     msg = "📌 *Ваши события:*\n\n"
#     for ev in events:
#         msg += (
#             f"🔹 *{ev['name']}*\n"
#             f"   📅 {ev['date']} | ⏰ {ev['time']} | ID: `{ev['id']}`\n"
#             f"   ℹ️ {ev['details']}\n\n"
#         )
#     update.message.reply_text(msg, parse_mode="Markdown")
#
#
# def create_event_handler(update: Update, context: CallbackContext):
#     """/create_event Название | Дата | Время | Описание"""
#     args = context.args
#     if not args or len(args) < 3:
#         update.message.reply_text(
#             "❌ Использование:\n"
#             "/create_event Название | Дата (ГГГГ-ММ-ДД) | Время (ЧЧ:ММ) | [Описание]\n\n"
#             "Пример:\n"
#             "/create_event Встреча | 2025-04-05 | 15:30 | Обсудить проект"
#         )
#         return
#
#     try:
#         raw = " ".join(args)
#         parts = raw.split(" | ")
#         if len(parts) < 3:
#             raise ValueError("Формат: Название | Дата | Время | Описание")
#
#         name = parts[0].strip()
#         date = parts[1].strip()
#         time = parts[2].strip()
#         details = parts[3].strip() if len(parts) > 3 else ""
#
#         event_id = calendar.create_event(name, date, time, details)
#         update.message.reply_text(
#             f"✅ Событие *'{name}'* создано!\n"
#             f"📅 Дата: {date}\n"
#             f"⏰ Время: {time}\n"
#             f"📌 ID события: `{event_id}`",
#             parse_mode="Markdown"
#         )
#     except ValueError as e:
#         update.message.reply_text(f"❌ Ошибка: {e}")
#     except Exception as e:
#         update.message.reply_text("❌ Не удалось создать событие. Проверьте формат.")
#
#
# def view_event_handler(update: Update, context: CallbackContext):
#     """/view_event <ID> — просмотр события"""
#     args = context.args
#     if not args:
#         update.message.reply_text("❌ Укажите ID события: `/view_event 1`", parse_mode="Markdown")
#         return
#
#     try:
#         event_id = int(args[0])
#         event = calendar.get_event(event_id)
#         if not event:
#             update.message.reply_text("❌ Событие не найдено.")
#             return
#
#         update.message.reply_text(
#             f"📋 *Событие #{event_id}*\n\n"
#             f"📌 Название: *{event['name']}*\n"
#             f"📅 Дата: {event['date']}\n"
#             f"⏰ Время: {event['time']}\n"
#             f"📄 Описание: {event['details']}",
#             parse_mode="HTML"
#         )
#     except ValueError:
#         update.message.reply_text("❌ ID должно быть числом.")
#
#
# def list_events_handler(update: Update, context: CallbackContext):
#     """/list_events — список всех событий"""
#     events = calendar.get_all_events()
#     if not events:
#         update.message.reply_text("🗓 У вас пока нет событий.")
#         return
#
#     message = "🗓 *Все события:*\n\n"
#     for ev in events:
#         message += (
#             f"🔹 *{ev['name']}*\n"
#             f"   📅 {ev['date']} | ⏰ {ev['time']} | ID: `{ev['id']}`\n\n"
#         )
#
#     update.message.reply_text(message, parse_mode="Markdown")
#
#
# def edit_event_handler(update: Update, context: CallbackContext):
#     """/edit_event ID | Новое название | Дата | Время | Описание"""
#     args = context.args
#     if not args or len(args) < 2:
#         update.message.reply_text(
#             "❌ Использование:\n"
#             "/edit_event ID | Название | Дата | Время | [Описание]"
#         )
#         return
#
#     try:
#         raw = " ".join(args)
#         parts = raw.split(" | ")
#         event_id = int(parts[0])
#
#         updates = {}
#         if len(parts) > 1: updates['event_name'] = parts[1].strip()
#         if len(parts) > 2: updates['event_date'] = parts[2].strip()
#         if len(parts) > 3: updates['event_time'] = parts[3].strip()
#         if len(parts) > 4: updates['event_details'] = parts[4].strip()
#
#         success = calendar.update_event(event_id, **updates)
#         if success:
#             update.message.reply_text(f"✅ Событие #{event_id} обновлено!")
#         else:
#             update.message.reply_text("❌ Событие не найдено.")
#     except Exception as e:
#         update.message.reply_text(f"❌ Ошибка: проверьте формат.")
#
#
# def delete_event_handler(update: Update, context: CallbackContext):
#     """/delete_event <ID> — удаление события"""
#     args = context.args
#     if not args:
#         update.message.reply_text("❌ Укажите ID: `/delete_event 1`", parse_mode="Markdown")
#         return
#
#     try:
#         event_id = int(args[0])
#         success = calendar.delete_event(event_id)
#         if success:
#             update.message.reply_text(f"🗑 Событие #{event_id} удалено.")
#         else:
#             update.message.reply_text("❌ Событие не найдено.")
#     except ValueError:
#         update.message.reply_text("❌ ID должно быть числом.")
#
