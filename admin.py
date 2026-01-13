# [file name]: admin.py
from myclass import *
import json
import time
from datetime import datetime
import pytz
from firebase_db import firebase_db

def admin_panel(message):
    """Панель администратора"""
    text = "⚙️ ПАНЕЛЬ АДМИНИСТРАТОРА\n\n"
    text += "Доступные команды:\n"
    text += "/admin premium [chat_id] - выдать Premium\n"
    text += "/admin money [user_id] [amount] - выдать деньги\n"
    text += "/admin cars - список всех машин\n"
    text += "/admin stats - статистика бота\n"
    text += "/admin ban [user_id] [дни] [причина]\n"
    text += "/admin checkban [user_id]\n"
    text += "/admin unban [user_id]\n"
    text += "/admin обнул [user_id]\n"
    text += "/admin mod [add/remove] [user_id] [status] [perm] - управление модераторами\n"
    text += "/admin db - просмотр базы данных"

    message.reply(text)

def handle_admin_command(message, args):
    """Обработка админских команд"""
    if len(args) < 2:
        return admin_panel(message)

    command = args[1]

    if command == "premium" and len(args) >= 3:
        chat_id = args[2]
        # Обновление премиума через Firebase
        success = firebase_db.update_data(f'chats/{chat_id}', {'premium': True})
        if success:
            message.reply(f"✅ Premium выдан чату {chat_id}")
        else:
            message.reply("❌ Ошибка при выдаче Premium")

    elif command == "money" and len(args) >= 4:
        try:
            user_input = args[2]
            amount = int(args[3])

            if amount <= 0:
                return message.reply("❌ Сумма должна быть положительной!")
            if amount > 1000000:
                return message.reply("❌ Слишком большая сумма! Максимум 1.000.000 руб.")

            # Получаем данные пользователя из Firebase
            user_id = message.extract_user_id(user_input)
            if not user_id:
                return message.reply("❌ Не удалось определить пользователя!")

            user_data = firebase_db.get_user(str(user_id))
            if not user_data:
                return message.reply("❌ Пользователь не найден!")

            # Выдаем деньги
            old_balance = user_data.get('money', 0)
            new_balance = old_balance + amount
            
            firebase_db.update_user_field(str(user_id), 'money', new_balance)

            username = user_data.get('username', 'Неизвестно')
            message.reply(
                f"✅ Деньги выданы успешно!\n\n"
                f"👤 Получатель: {username}\n"
                f"💰 Сумма: {format_number(amount)} руб.\n"
                f"📊 Баланс: {format_number(old_balance)} → {format_number(new_balance)} руб.\n"
                f"🆔 ID: {user_id}"
            )

        except ValueError:
            message.reply("❌ Неверный формат суммы! Укажите число.")
        except Exception as e:
            message.reply(f"❌ Ошибка при выдаче денег: {str(e)}")

    elif command == "cars":
        cars_data = firebase_db.get_car_shop()
        text = "🚗 ВСЕ МАШИНЫ В МАГАЗИНЕ:\n\n"
        for car_id, car in cars_data.items():
            text += f"{car_id}. {car['name']} - {car['price']} руб.\n"
        message.reply(text)

    elif command == "stats":
        users_data = firebase_db.get_all_users()
        chats_data = firebase_db.get_all_chats()

        text = "📊 СТАТИСТИКА БОТА:\n\n"
        text += f"👤 Пользователей: {len(users_data) if users_data else 0}\n"
        text += f"💬 Чатов: {len(chats_data) if chats_data else 0}\n"
        # Активные гонки нужно брать из отдельной коллекции
        text += f"🏎️ Активных гонок: 0\n"
        text += f"🌍 Глобальных гонок: 0\n"

        message.reply(text)
        
    elif command == "обнул":
        user_id = message.extract_user_id(args[2])
        user_id_str = str(user_id)
        
        user_data = firebase_db.get_user(user_id_str)
        if not user_data:
            return message.reply("Этого юзера нет в базе данных!")
        
        # Обнуляем пользователя
        updates = {
            'money': 0,
            'exp': 0,
            'level': 0,
            'pistons': 0,
            'cars': {},
            'active_car': None
        }
        
        firebase_db.update_data(f'users/{user_id_str}', updates)
        message.reply(f"[id{user_id}|{message.get_mention(user_id)}] успешно обнулён!")
    
    elif command == "mod":
        if len(args) < 5:
            return message.reply("❌ Использование: /admin mod [add/remove] [user_id] [status] [perm]\n"
                               "📌 status: owner/zam/admin/moder\n"
                               "📌 perm: all/basic")
        
        action = args[2].lower()
        user_id = message.extract_user_id(args[3])
        status = args[4].lower()
        perm = args[5].lower() if len(args) > 5 else "basic"
        
        # Проверка валидности статуса
        valid_statuses = ["owner", "zam", "admin", "moder"]
        if status not in valid_statuses:
            return message.reply(f"❌ Неверный статус! Допустимые значения: {', '.join(valid_statuses)}")
        
        # Проверка валидности прав
        valid_perms = ["all", "basic"]
        if perm not in valid_perms:
            return message.reply(f"❌ Неверные права! Допустимые значения: {', '.join(valid_perms)}")
        
        if action == "add":
            # Проверяем, не является ли уже модератором
            if firebase_db.is_moderator(str(user_id)):
                return message.reply(f"❌ Пользователь [id{user_id}|Уже] является модератором!")
            
            # Добавляем модератора
            success = firebase_db.add_moderator(str(user_id), status, perm)
            
            if success:
                # Получаем имя пользователя
                user_data = firebase_db.get_user(str(user_id))
                username = user_data.get('username', f"id{user_id}")
                
                message.reply(f"✅ Пользователь [id{user_id}|{username}] назначен модератором!\n"
                             f"📊 Статус: {status}\n"
                             f"🔑 Права: {perm}")
            else:
                message.reply("❌ Ошибка при добавлении модератора")
            
        elif action == "remove":
            # Проверяем, является ли модератором
            if not firebase_db.is_moderator(str(user_id)):
                return message.reply(f"❌ Пользователь [id{user_id}|Не] является модератором!")
            
            # Получаем информацию перед удалением
            admin_data = firebase_db.get_admin_data()
            user_status = admin_data.get('moders', {}).get(str(user_id), {}).get('status', 'unknown')
            
            # Удаляем модератора
            success = firebase_db.remove_moderator(str(user_id))
            
            if success:
                # Получаем имя пользователя
                user_data = firebase_db.get_user(str(user_id))
                username = user_data.get('username', f"id{user_id}")
                
                message.reply(f"✅ Пользователь [id{user_id}|{username}] снят с должности модератора!\n"
                             f"📊 Бывший статус: {user_status}")
            else:
                message.reply("❌ Ошибка при удалении модератора")
        
        else:
            return message.reply("❌ Неверное действие! Используйте 'add' или 'remove'")
    
    elif command == "db":
        try:
            # Получаем все данные из Firebase
            admin_data = firebase_db.get_admin_data()
            
            # Форматируем JSON с отступами
            formatted_db = json.dumps(admin_data, indent=2, ensure_ascii=False)
            
            # Разбиваем на части если слишком длинное
            if len(formatted_db) > 4000:
                parts = []
                current_part = ""
                
                for line in formatted_db.split('\n'):
                    if len(current_part) + len(line) + 1 > 4000:
                        parts.append(current_part)
                        current_part = line + '\n'
                    else:
                        current_part += line + '\n'
                
                if current_part:
                    parts.append(current_part)
                
                # Отправляем первую часть с информацией
                message.reply(f"📁 ДАННЫЕ ИЗ FIREBASE\n"
                             f"📊 Всего частей: {len(parts)}\n\n"
                             f"Часть 1 из {len(parts)}:\n"
                             f"```json\n{parts[0]}\n```")
                
                # Отправляем остальные части
                for i in range(1, len(parts)):
                    message.reply(f"📁 Часть {i+1} из {len(parts)}:\n"
                                 f"```json\n{parts[i]}\n```")
            else:
                message.reply(f"📁 ДАННЫЕ ИЗ FIREBASE\n\n"
                             f"```json\n{formatted_db}\n```")
            
        except Exception as e:
            message.reply(f"❌ Ошибка при чтении базы данных: {str(e)}")

    elif command == "ban":
        if len(args) < 5:
            return message.reply("❌ Использование: /admin ban [user_id] [кол-во дней] [причина]")

        user_id = message.extract_user_id(args[2])

        try:
            days = int(args[3])
            if days <= 0:
                return message.reply("❌ Количество дней должно быть положительным числом!")
        except ValueError:
            return message.reply("❌ Количество дней должно быть числом!")

        reason = " ".join(args[4:])

        # Проверяем, забанен ли пользователь
        if firebase_db.is_user_banned(str(user_id)):
            # Получаем информацию о текущем бане
            ban_data = firebase_db.get_data(f'admin/ban/{user_id}')
            if ban_data:
                old_dt = datetime.fromtimestamp(ban_data.get('time', 0), tz=pytz.timezone('Europe/Moscow'))

                reply_text = (
                    f"⚠️ Пользователь уже забанен!\n"
                    f"📋 Текущий бан:\n"
                    f"• Причина: {ban_data.get('reason', 'Не указана')}\n"
                    f"• Дата: {old_dt.strftime('%d.%m.%Y %H:%M:%S')}\n"
                    f"• Срок: {ban_data.get('days', 0)} дней\n\n"
                    f"🔄 Начинаю процесс перебана..."
                )
                message.reply(reply_text)

        # Создаем новый бан
        success = firebase_db.ban_user(str(user_id), days, reason)

        if success:
            current_time = int(time.time())
            end_time = current_time + (days * 24 * 60 * 60)
            ban_dt = datetime.fromtimestamp(current_time, tz=pytz.timezone('Europe/Moscow'))
            end_dt = datetime.fromtimestamp(end_time, tz=pytz.timezone('Europe/Moscow'))

            success_text = (
                f"✅ [id{user_id}|Пользователь] успешно заблокирован!\n\n"
                f"📊 Информация о бане:\n"
                f"• Дата: {ban_dt.strftime('%d.%m.%Y %H:%M:%S')}\n"
                f"• До: {end_dt.strftime('%d.%m.%Y %H:%M:%S')}\n"
                f"• Срок: {days} дней\n"
                f"• Причина: {reason}\n\n"
                f"⏰ Бан истечет через {days} дней"
            )

            return message.reply(success_text)
        else:
            return message.reply("❌ Ошибка при бане пользователя")

    elif command == "unban":
        if len(args) < 3:
            return message.reply("❌ Использование: /admin unban [user_id]")

        user_id = message.extract_user_id(args[2])

        # Проверяем, забанен ли пользователь
        if not firebase_db.is_user_banned(str(user_id)):
            return message.reply("❌ Пользователь не забанен!")

        # Получаем информацию о бане перед удалением
        ban_data = firebase_db.get_data(f'admin/ban/{user_id}')
        
        if ban_data:
            ban_time = ban_data.get('time', 0)
            ban_days = ban_data.get('days', 0)
            ban_reason = ban_data.get('reason', 'Не указана')

            # Вычисляем время окончания бана
            end_time = ban_time + (ban_days * 24 * 60 * 60)
            current_time = time.time()
            remaining = end_time - current_time

            # Форматируем даты
            start_dt = datetime.fromtimestamp(ban_time, tz=pytz.timezone('Europe/Moscow'))
            end_dt = datetime.fromtimestamp(end_time, tz=pytz.timezone('Europe/Moscow'))

            # Удаляем пользователя из бана
            success = firebase_db.unban_user(str(user_id))

            if success:
                # Формируем сообщение
                t = f"✅ [id{user_id}|Пользователь] успешно разблокирован!\n\n"
                t += f"📊 Информация о снятом бане:\n"
                t += f"• Дата бана: {start_dt.strftime('%d.%m.%Y %H:%M:%S')}\n"
                t += f"• Плановый конец: {end_dt.strftime('%d.%m.%Y %H:%M:%S')}\n"
                t += f"• Причина: {ban_reason}\n"
                t += f"• Срок: {ban_days} дней\n"

                if remaining > 0:
                    days_left = int(remaining // (24 * 60 * 60))
                    hours_left = int((remaining % (24 * 60 * 60)) // (60 * 60))
                    t += f"• Снят досрочно: за {days_left}д {hours_left}ч до окончания"
                else:
                    t += f"• Бан истек: снятие по окончании срока"

                return message.reply(t)
            else:
                return message.reply("❌ Ошибка при разбане пользователя")
        else:
            return message.reply("❌ Информация о бане не найдена")

    elif command == "checkban":
        if len(args) < 3:
            return message.reply("❌ Использование: /admin checkban [user_id]")

        user_id = message.extract_user_id(args[2])

        # Проверяем, забанен ли пользователь
        ban_data = firebase_db.get_data(f'admin/ban/{user_id}')
        if not ban_data:
            return message.reply("❌ Пользователь не забанен!")

        ban_time = ban_data.get('time', 0)
        days = ban_data.get('days', 0)

        # Вычисляем время окончания бана
        end_time = ban_time + (days * 24 * 60 * 60)
        current_time = time.time()

        # Время в читаемом формате
        start_dt = datetime.fromtimestamp(ban_time, tz=pytz.timezone('Europe/Moscow'))
        end_dt = datetime.fromtimestamp(end_time, tz=pytz.timezone('Europe/Moscow'))

        # Вычисляем оставшееся время
        remaining = end_time - current_time

        if remaining <= 0:
            time_left = "⏰ Бан истек"
            progress = "██████████"  # 100%
        else:
            total_duration = days * 24 * 60 * 60
            progress_percent = (1 - remaining / total_duration) * 100
            progress_bars = int(progress_percent / 10)
            progress = "█" * progress_bars + "░" * (10 - progress_bars)

            # Форматируем оставшееся время
            if remaining > 86400:  # больше суток
                time_left = f"⏳ Осталось: {int(remaining // 86400)} дн. {int((remaining % 86400) // 3600)} час."
            elif remaining > 3600:  # больше часа
                time_left = f"⏳ Осталось: {int(remaining // 3600)} час. {int((remaining % 3600) // 60)} мин."
            else:  # меньше часа
                time_left = f"⏳ Осталось: {int(remaining // 60)} мин. {int(remaining % 60)} сек."

        t = f"🚫 Информация о бане [id{user_id}|Пользователя]\n\n"
        t += f"📅 Начало: {start_dt.strftime('%d.%m.%Y %H:%M')}\n"
        t += f"📅 Конец: {end_dt.strftime('%d.%m.%Y %H:%M')}\n"
        t += f"⏰ {time_left}\n"

        if remaining > 0:
            t += f"📊 Прогресс: [{progress}] {min(100, int(progress_percent))}%\n"

        t += f"📝 Причина: {ban_data.get('reason', 'Не указана')}\n"
        t += f"⏱️ Срок: {days} дней"

        return message.reply(t)
    else:
        return admin_panel(message)
