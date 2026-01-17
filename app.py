from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import json
import os
import time
import datetime
import threading
import requests
from yoomoney import Quickpay
from admin import handle_admin_command
from myfunctions import *
from myclass import *
from config import BOT_TOKEN as token, admins_ids, GROUP_ID

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'garage-site-2024-secret-key-min-32-chars!!')

# =============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# =============================================================================

vk_session = vk_api.VkApi(token=token)
vk = vk_session.get_api()

print(f"🔧 Инициализирован VK API с токеном: {token[:20]}...")

YOOMONEY_RECEIVER = "4100119211392665"
YOOMONEY_SECRET = "23DF37D7EBE0F6DE798D0777123EBF2D6812B95852784C60B4C7091A7A6B69EB"

DONATE_PACKAGES = {
    "money": {"name": "Деньги", 'price': 1, 'money': 50, 'cars': [], 'description': "1₽ = 50₽", 'dynamic': True},
    "starter": {"name": "Стартовый набор", "price": 100, "money": 5000, "cars": [], "description": "Набор для новичков", 'dynamic': False},
    "racer": {"name": "Набор гонщика", "price": 300, "money": 15000, "cars": ["Kia Rio"], "description": "Для опытных гонщиков", 'dynamic': False},
    "pro": {"name": "PRO набор", "price": 500, "money": 30000, "cars": ["BMW 3 Series"], "description": "Для профессионалов", 'dynamic': False},
    "vip": {"name": "VIP набор", "price": 1000, "money": 50000, "cars": ["Porsche 911"], "description": "Элитный набор", 'dynamic': False}
}

CAR_COLORS = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF",
              "#FFA500", "#800080", "#FFC0CB", "#A52A2A", "#000000", "#FFFFFF",
              "#808080", "#FFD700", "#008000", "#000080"]

database_login = {}

# =============================================================================
# WEBHOOK РОУТЫ ДЛЯ VK БОТА - УПРОЩЁННЫЙ ВАРИАНТ
# =============================================================================

@app.route('/vk-webhook', methods=['POST', 'GET'])
def vk_webhook():
    """Основной вебхук для VK API"""
    print(f"📥 [WEBHOOK] Получен запрос: {request.method}")
    
    if request.method == 'GET':
        # Для подтверждения вебхука
        print(f"🔑 [WEBHOOK] Запрос подтверждения от VK")
        return '9bb1bfa1'
    
    try:
        data = request.json
        print(f"📦 [WEBHOOK] Получены данные: {json.dumps(data, ensure_ascii=False)[:500]}")
        
        if not data:
            print("❌ [WEBHOOK] Нет JSON данных")
            return jsonify({'response': 'error', 'message': 'No JSON data'}), 400
        
        # Проверка типа события
        event_type = data.get('type')
        print(f"🎯 [WEBHOOK] Тип события: {event_type}")
        
        if event_type == 'confirmation':
            # Возвращаем строку подтверждения для настройки вебхука
            print(f"✅ [WEBHOOK] Отправляем подтверждение")
            return '9bb1bfa1'
        
        elif event_type == 'message_new':
            # Обработка нового сообщения
            print(f"💬 [WEBHOOK] Новое сообщение")
            
            try:
                # Проверяем структуру данных
                if 'object' not in data or 'message' not in data['object']:
                    print(f"❌ [WEBHOOK] Неправильная структура сообщения")
                    return jsonify({'response': 'ok'})
                
                message_obj = data['object']['message']
                
                # Проверяем, не отправитель ли это бот
                from_id = message_obj.get('from_id')
                peer_id = message_obj.get('peer_id')
                text = message_obj.get('text', '')
                
                print(f"👤 [WEBHOOK] Сообщение от {from_id} в {peer_id}: {text}")
                
                # Проверяем, не бот ли это
                if from_id < 0:
                    print(f"🤖 [WEBHOOK] Сообщение от бота, игнорируем")
                    return jsonify({'response': 'ok'})
                
                # Создаем структуру данных
                message_data = {
                    'from_id': from_id,
                    'peer_id': peer_id,
                    'text': text,
                    'conversation_message_id': message_obj.get('conversation_message_id'),
                    'id': message_obj.get('id'),
                }
                
                if 'payload' in message_obj and message_obj['payload']:
                    message_data['payload'] = message_obj['payload']
                    print(f"🎯 [WEBHOOK] Есть payload: {message_obj['payload']}")
                
                # Запускаем обработку в отдельном потоке
                threading.Thread(target=process_vk_message, args=(message_data,)).start()
                
                print(f"✅ [WEBHOOK] Сообщение принято в обработку")
                return jsonify({'response': 'ok'})
                
            except Exception as e:
                print(f"❌ [WEBHOOK] Ошибка обработки message_new: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'response': 'ok'})  # Все равно отвечаем OK
        
        elif event_type == 'message_event':
            # Обработка callback кнопок
            print(f"🔄 [WEBHOOK] Callback кнопка")
            
            try:
                event_obj = data['object']
                event_data = {
                    'user_id': event_obj['user_id'],
                    'peer_id': event_obj['peer_id'],
                    'event_id': event_obj['event_id'],
                    'conversation_message_id': event_obj.get('conversation_message_id'),
                    'payload': event_obj['payload']
                }
                
                print(f"🔄 [WEBHOOK] Callback от пользователя {event_data['user_id']}")
                
                # Подтверждаем callback сразу
                try:
                    vk.messages.sendMessageEventAnswer(
                        event_id=event_data['event_id'],
                        user_id=event_data['user_id'],
                        peer_id=event_data['peer_id'],
                        event_data=json.dumps({"type": "show_snackbar", "text": "✅ Обработано"})
                    )
                    print(f"✅ [WEBHOOK] Callback подтвержден")
                except Exception as e:
                    print(f"⚠️ [WEBHOOK] Ошибка подтверждения callback: {e}")
                
                # Запускаем обработку в отдельном потоке
                threading.Thread(target=process_vk_callback, args=(event_data,)).start()
                
                return jsonify({'response': 'ok'})
                
            except Exception as e:
                print(f"❌ [WEBHOOK] Ошибка обработки message_event: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'response': 'ok'})
        
        else:
            print(f"ℹ️ [WEBHOOK] Неизвестный тип события: {event_type}")
            return jsonify({'response': 'ok'})
            
    except Exception as e:
        print(f"🔥 [WEBHOOK] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'response': 'error', 'message': str(e)}), 500

def process_vk_message(message_data):
    """Обработка сообщения VK в отдельном потоке"""
    try:
        print(f"⚙️ [PROCESS] Начало обработки сообщения: {message_data}")
        
        # Проверяем токен
        if not token:
            print(f"❌ [PROCESS] Токен бота не найден!")
            return
        
        # Создаем новую сессию для этого потока
        try:
            local_vk_session = vk_api.VkApi(token=token)
            local_vk = local_vk_session.get_api()
            print(f"✅ [PROCESS] Создана локальная сессия VK")
        except Exception as e:
            print(f"❌ [PROCESS] Ошибка создания сессии VK: {e}")
            return
        
        # Создаем объект Message
        message = Message(message_data, local_vk)
        text = message_data.get('text', '').lower()
        
        print(f"📝 [PROCESS] Текст сообщения: {text}")
        
        # Проверяем действие (action) для приветствия при добавлении бота
        if 'action' in message_data and message_data['action']:
            action_type = message_data['action'].get('type')
            if action_type == 'chat_invite_user':
                new_member_id = message_data['action'].get('member_id')
                if new_member_id == -int(GROUP_ID):
                    print(f"👋 [PROCESS] Бота добавили в чат, отправляем приветствие")
                    send_welcome_message(message)
                    return
        
        # Обработка payload для кнопок
        if 'payload' in message_data and message_data['payload']:
            try:
                payload_str = message_data['payload']
                print(f"🎯 [PROCESS] Raw payload: {payload_str}")
                
                # Иногда payload может быть уже строкой JSON
                if isinstance(payload_str, str):
                    payload = json.loads(payload_str)
                else:
                    payload = payload_str
                    
                print(f"🎯 [PROCESS] Parsed payload: {payload}")
                
                if 'cmd' in payload:
                    cmd = payload['cmd']
                    print(f"🎯 [PROCESS] Команда из payload: {cmd}")
                    handle_button_command(message, cmd, payload)
                    return
            except Exception as e:
                print(f"⚠️ [PROCESS] Ошибка парсинга payload: {e}")
        
        # ПРОСТОЙ ТЕСТ: ответить на любое сообщение
        print(f"🔄 [PROCESS] Пробуем ответить...")
        try:
            # Просто отправляем эхо-ответ для теста
            response_text = f"Получил ваше сообщение: '{text}'\nID: {message_data['from_id']}"
            local_vk.messages.send(
                peer_id=message_data['peer_id'],
                message=response_text,
                random_id=0
            )
            print(f"✅ [PROCESS] Тестовое сообщение отправлено!")
        except Exception as e:
            print(f"❌ [PROCESS] Ошибка отправки тестового сообщения: {e}")
        
        # Обработка текстовых команд через существующую функцию
        print(f"🔄 [PROCESS] Вызываем handle_message_event")
        handle_message_event(message_data)
        print(f"✅ [PROCESS] Обработка завершена")
        
    except Exception as e:
        print(f"🔥 [PROCESS] Ошибка обработки сообщения: {e}")
        import traceback
        traceback.print_exc()

def process_vk_callback(event_data):
    """Обработка callback кнопок VK в отдельном потоке"""
    try:
        print(f"⚙️ [CALLBACK] Начало обработки callback: {event_data}")
        
        # Создаем локальную сессию
        local_vk_session = vk_api.VkApi(token=token)
        local_vk = local_vk_session.get_api()
        
        # Создаем структуру данных для совместимости
        message_data = {
            'from_id': event_data['user_id'],
            'user_id': event_data['user_id'],
            'peer_id': event_data['peer_id'],
            'payload': event_data.get('payload'),
            'conversation_message_id': event_data.get('conversation_message_id'),
            'event_id': event_data['event_id']
        }
        
        message = Message(message_data, local_vk)
        
        # Обрабатываем callback
        handle_callback_event(message_data)
        
    except Exception as e:
        print(f"🔥 [CALLBACK] Ошибка обработки callback: {e}")
        import traceback
        traceback.print_exc()

def send_welcome_message(message):
    """Отправка приветственного сообщения при добавлении бота в чат"""
    try:
        peer_id = message.peer_id
        
        welcome_text = """@all 🏎️ ДОБРО ПОЖАЛОВАТЬ В ГОНОЧНЫЙ БОТ!

Приветствую всех участников чата! 🎉

Я — бот для организации захватывающих гонок и соревнований.

🚀 ОСНОВНЫЕ ВОЗМОЖНОСТИ:
• 🏎️ Создавать гонки прямо в чате
• 🚗 Покупать и улучшать автомобили
• ⚔️ Устраивать драг-рейсинг
• 🏆 Создавать кланы и битвы кланов

📋 КОМАНДЫ ДЛЯ ЧАТА:
• "Гонка" - создать/присоединиться к гонке
• "Меню" - показать главное меню
• "Драг @игрок" - вызвать на драг-рейсинг
• "Клан" - система кланов

🎮 Удачи на треках! 🏁"""

        keyboard = VkKeyboard(inline=True)
        keyboard.add_button("🏎️ Создать гонку", VkKeyboardColor.POSITIVE, payload={'cmd': 'create_race'})
        keyboard.add_line()
        keyboard.add_button("📋 Команды", VkKeyboardColor.PRIMARY, payload={'cmd': 'show_commands'})
        
        # Создаем локальную сессию
        local_vk_session = vk_api.VkApi(token=token)
        local_vk = local_vk_session.get_api()
        
        local_vk.messages.send(
            peer_id=peer_id,
            message=welcome_text,
            keyboard=keyboard.get_keyboard(),
            random_id=0
        )
        
        print(f"✅ Приветственное сообщение отправлено в чат {peer_id}")
        
    except Exception as e:
        print(f"❌ Ошибка отправки приветствия: {e}")

# =============================================================================
# ДОПОЛНИТЕЛЬНЫЙ ТЕСТОВЫЙ РОУТ
# =============================================================================

@app.route('/test-bot', methods=['GET'])
def test_bot():
    """Тестовый роут для проверки работы бота"""
    try:
        # Пробуем отправить тестовое сообщение
        test_user_id = 819016396  # Ваш ID
        test_message = "🤖 Бот работает! Сервер отвечает."
        
        local_vk_session = vk_api.VkApi(token=token)
        local_vk = local_vk_session.get_api()
        
        local_vk.messages.send(
            user_id=test_user_id,
            message=test_message,
            random_id=0
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Тестовое сообщение отправлено'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def load_payments():
    try:
        with open('payments.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"payments": {}, "last_check": 0}

def save_payments(data):
    with open('payments.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_by_id(user_id):
    users_data = load_data(USERS_DB_FILE)
    return users_data.get('users', {}).get(str(user_id))

def update_user_data(user_id, user_data):
    users_data = load_data(USERS_DB_FILE)
    users_data['users'][str(user_id)] = user_data
    save_data(users_data, USERS_DB_FILE)

def get_car_colors(user_id):
    users_data = load_data(USERS_DB_FILE)
    user = users_data.get('users', {}).get(str(user_id), {})
    return user.get('car_colors', {})

def save_car_color(user_id, car_id, color):
    users_data = load_data(USERS_DB_FILE)
    user = users_data.get('users', {}).get(str(user_id), {})
    
    if 'car_colors' not in user:
        user['car_colors'] = {}
    
    user['car_colors'][car_id] = color
    users_data['users'][str(user_id)] = user
    save_data(users_data, USERS_DB_FILE)

# =============================================================================
# FLASK РОУТЫ ДЛЯ САЙТА (упрощённые)
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '').strip()
        
        flash(f"Вход для пользователя {user_id}", 'info')
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/garage')
def garage():
    return render_template('garage.html')

@app.route('/health')
def health_check():
    return 'OK', 200

@app.route('/debug-webhook', methods=['POST'])
def debug_webhook():
    """Роут для отладки вебхука"""
    print("=" * 50)
    print("🔧 DEBUG WEBHOOK REQUEST")
    print(f"Method: {request.method}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Content-Type: {request.content_type}")
    
    if request.is_json:
        data = request.json
        print(f"JSON Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
    else:
        print(f"Raw Data: {request.data}")
    
    print("=" * 50)
    
    return jsonify({
        'status': 'received',
        'method': request.method,
        'content_type': request.content_type,
        'has_json': request.is_json
    })

# =============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    
    print("=" * 50)
    print(f"🌐 Запуск веб-сервера на порту {port}...")
    print(f"🤖 ВК бот работает через вебхук")
    print(f"📌 Webhook URL: https://racebotvk.onrender.com/vk-webhook")
    print(f"🔑 Код подтверждения: 9bb1bfa1")
    print(f"🔧 Токен бота: {token[:20]}...")
    print(f"👥 ID группы: {GROUP_ID}")
    print("=" * 50)
    
    # Проверяем токен
    try:
        # Пробуем сделать простой запрос к API
        test_result = vk.users.get(user_ids=1)
        print(f"✅ Токен действителен: {test_result}")
    except Exception as e:
        print(f"❌ Ошибка проверки токена: {e}")
    
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
