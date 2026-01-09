from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json
import os
import time
import datetime
import threading
import requests
from yoomoney import Client, Quickpay
from admin import handle_admin_command
from myfunctions import *
from myclass import *
from config import BOT_TOKEN as token, admins_ids, GROUP_ID

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ VK БОТА (LONGPOLL)
# =============================================================================

# Глобальные переменные для бота
vk_session = vk_api.VkApi(token=token)
vk = vk_session.get_api()
longpoll = None
bot_thread = None
import os
import sys
import time
import signal
from threading import Thread
import datetime

# =============================================================================
# АВТОМАТИЧЕСКИЙ ПЕРЕЗАПУСК ДЛЯ CLOUD SHELL
# =============================================================================

class AutoRestart:
    def __init__(self, max_hours=45):
        """
        max_hours: через сколько часов перезапускаться
        45 часов (вместо 50) для безопасности
        """
        self.max_hours = max_hours
        self.start_time = time.time()
        self.restart_count = 0
        
    def start(self):
        """Запуск автоматического перезапуска"""
        def restart_thread():
            while True:
                # Текущее время работы
                current_time = time.time()
                hours_running = (current_time - self.start_time) / 3600
                
                # Каждые 30 минут пишем в лог
                if int(time.time()) % 1800 == 0:
                    print(f"[{datetime.datetime.now()}] Бот работает {hours_running:.1f} часов")
                
                # Если работали больше max_hours - перезапускаемся
                if hours_running > self.max_hours:
                    print(f"⏰ Время сессии истекает! ({hours_running:.1f} часов)")
                    print("🔄 Начинаю автоматический перезапуск...")
                    self.perform_restart()
                
                # Проверяем каждую минуту
                time.sleep(60)
        
        # Запускаем в отдельном потоке
        Thread(target=restart_thread, daemon=True).start()
        print(f"✅ Автоперезапуск настроен на каждые {self.max_hours} часов")
    
    def perform_restart(self):
        """Выполнить перезапуск"""
        # Сохраняем важные данные перед перезапуском
        print("💾 Сохраняю данные...")
        time.sleep(2)
        
        # Перезапускаем процесс
        print("🚀 Перезапускаю бота...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

# Создаем глобальный объект авто-перезапуска
auto_restart = AutoRestart(max_hours=30)  # 30 часов
def init_bot():
    """Инициализировать бота"""
    global longpoll, vk_session, vk
    try:
        vk_session = vk_api.VkApi(token=token)
        vk = vk_session.get_api()
        longpoll = VkBotLongPoll(vk_session, GROUP_ID)
        print("✅ VK бот инициализирован (LongPoll)")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации бота: {e}")
        return False

def run_bot():
    """Запустить бота в отдельном потоке"""
    print("🚀 Запуск бота VK...")
    
    while True:
        try:
            if not longpoll:
                if not init_bot():
                    time.sleep(10)
                    continue
            
            print("📱 Бот ожидает сообщения...")
            
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    handle_vk_message(event)
                elif event.type == VkBotEventType.MESSAGE_EVENT:
                    handle_vk_callback(event)
                    
        except Exception as e:
            print(f"❌ Ошибка в боте: {e}")
            time.sleep(5)
            init_bot()

def handle_vk_message(event):
    """Обработка сообщений VK"""
    try:
        # Создаем структуру данных, совместимую с существующей логикой
        message_data = {
            'from_id': event.obj.message['from_id'],
            'peer_id': event.obj.message['peer_id'],
            'text': event.obj.message['text'],
            'conversation_message_id': event.obj.message.get('conversation_message_id'),
            'id': event.obj.message.get('id'),
        }
        
        # Если есть payload, добавляем его
        if 'payload' in event.obj.message and event.obj.message['payload']:
            message_data['payload'] = event.obj.message['payload']
        
        # Создаем объект Message
        message = Message(message_data, vk)
        
        text = event.obj.message['text'].lower() if event.obj.message['text'] else ""
        
        # Обработка payload для кнопок
        if 'payload' in event.obj.message and event.obj.message['payload']:
            try:
                payload = json.loads(event.obj.message['payload'])
                if 'cmd' in payload:
                    handle_button_command(message, payload['cmd'], payload)
                    return
            except:
                pass
        
        # Вызываем существующую функцию обработки сообщений
        handle_message_event(message_data)
        
    except Exception as e:
        print(f"❌ Ошибка обработки сообщения: {e}")
        import traceback
        print(f"Трассировка: {traceback.format_exc()}")

def handle_vk_callback(event):
    """Обработка callback кнопок VK"""
    try:
        # Создаем структуру данных для совместимости
        message_data = {
            'from_id': event.object['user_id'],
            'user_id': event.object['user_id'],
            'peer_id': event.object['peer_id'],
            'payload': event.object.get('payload'),
            'conversation_message_id': event.object.get('conversation_message_id')
        }
        
        # Создаем объект Message
        message = Message(message_data, vk)
        
        
        handle_callback_event(message_data)
            
        
        
        
    except Exception as e:
        print(f"❌ Ошибка обработки callback: {e}")
        import traceback
        print(f"Трассировка: {traceback.format_exc()}")

# =============================================================================
# НАСТРОЙКИ ЮMONEY
# =============================================================================

YOOMONEY_RECEIVER = "4100119211392665"
YOOMONEY_SECRET = "23DF37D7EBE0F6DE798D0777123EBF2D6812B95852784C60B4C7091A7A6B69EB"

DONATE_PACKAGES = {
    "money": {
        "name": "Деньги",
        'price': 1,
        'money': 50,
        'cars': [],
        'description': "1₽ = 50₽",
        'dynamic': True
    },
    "starter": {
        "name": "Стартовый набор",
        "price": 100,
        "money": 5000,
        "cars": [],
        "description": "Набор для новичков",
        'dynamic': False
    },
    "racer": {
        "name": "Набор гонщика",
        "price": 300,
        "money": 15000,
        "cars": ["Kia Rio"],
        "description": "Для опытных гонщиков",
        'dynamic': False
    },
    "pro": {
        "name": "PRO набор",
        "price": 500,
        "money": 30000,
        "cars": ["BMW 3 Series"],
        "description": "Для профессионалов",
        'dynamic': False
    },
    "vip": {
        "name": "VIP набор",
        "price": 1000,
        "money": 50000,
        "cars": ["Porsche 911"],
        "description": "Элитный набор",
        'dynamic': False
    }
}

CAR_COLORS = [
    "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF",
    "#FFA500", "#800080", "#FFC0CB", "#A52A2A", "#000000", "#FFFFFF",
    "#808080", "#FFD700", "#008000", "#000080"
]

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

# Хранилище для логинов на сайте
database_login = {}

# =============================================================================
# ВСЕ ВАШИ РОУТЫ (ПОЛНОСТЬЮ СОХРАНЕНЫ)
# =============================================================================

@app.route('/vk_auth', methods=['POST'])
def vk_auth():
    """Обработка данных от VK ID"""
    try:
        data = request.json
        access_token = data.get('access_token')
        vk_user_id = data.get('user_id')
        
        if not access_token or not vk_user_id:
            return jsonify({'success': False, 'error': 'Недостаточно данных'})
        
        print(f"[VK AUTH] Получен запрос от пользователя {vk_user_id}")
        
        # Проверяем токен через VK API
        verify_url = 'https://api.vk.com/method/users.get'
        params = {
            'access_token': access_token,
            'v': '5.199'
        }
        
        response = requests.get(verify_url, params=params)
        verify_data = response.json()
        
        if 'response' in verify_data:
            # Токен валидный, получаем информацию о пользователе
            user_info_url = 'https://api.vk.com/method/users.get'
            user_params = {
                'access_token': access_token,
                'user_ids': vk_user_id,
                'fields': 'first_name,last_name,photo_200',
                'v': '5.199'
            }
            
            user_response = requests.get(user_info_url, params=user_params)
            user_data = user_response.json()
            
            if 'response' in user_data and user_data['response']:
                user = user_data['response'][0]
                username = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                
                # Проверяем, есть ли пользователь в нашей базе
                existing_user = get_user_by_id(vk_user_id)
                
                if not existing_user:
                    # Создаем нового пользователя
                    print(f"[VK AUTH] Создание нового пользователя {vk_user_id}")
                    users_data = load_data(USERS_DB_FILE)
                    
                    new_user = {
                        "username": username,
                        "money": 1000,  # Стартовый баланс
                        "exp": 0,
                        "level": 1,
                        "cars": {
                            "1": {
                                "name": "Lada Vesta",
                                "hp": 106,
                                "max_speed": 180,
                                "tire_health": 100,
                                "durability": 100,
                                "bought_date": datetime.datetime.now().isoformat()
                            }
                        },
                        "active_car": "1",
                        "referral_code": f"ref_{vk_user_id}",
                        "referred_by": None,
                        "pistons": 0
                    }
                    
                    users_data['users'][str(vk_user_id)] = new_user
                    save_data(users_data, USERS_DB_FILE)
                    
                    print(f"[VK AUTH] Создан новый пользователь: {username} (ID: {vk_user_id})")
                
                # Авторизуем пользователя
                session['user_id'] = vk_user_id
                session['vk_token'] = access_token
                session.permanent = True
                
                # Сохраняем в базе логинов для совместимости
                database_login[str(vk_user_id)] = {
                    'status': 'success',
                    'timestamp': time.time(),
                    'username': username
                }
                
                return jsonify({
                    'success': True,
                    'user_id': vk_user_id,
                    'username': username
                })
        
        return jsonify({'success': False, 'error': 'Ошибка проверки токена'})
        
    except Exception as e:
        print(f"[VK AUTH] Ошибка: {e}")
        import traceback
        print(f"Трассировка: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/vk_auth_callback')
def vk_auth_callback():
    """Callback URL для VK ID (режим callback)"""
    # В режиме callback VK ID уже обработал авторизацию через JS
    # Перенаправляем пользователя обратно
    return redirect(url_for('index'))

@app.route('/vk_logout')
def vk_logout():
    """Выход из системы"""
    session.clear()
    flash('Вы успешно вышли из системы!', 'success')
    return redirect(url_for('index'))

# ДОБАВЬТЕ ЭТУ ФУНКЦИЮ В utility_processor ДЛЯ ПРОВЕРКИ VK ТОКЕНА:
@app.context_processor
def utility_processor():
    def check_is_admin(user_id):
        return is_admin(user_id)

    def check_can_edit_admins(user_id):
        return can_edit_admins(user_id)
    
    def get_vk_user_photo(user_id):
        """Получение фото пользователя из сессии VK"""
        if 'vk_token' in session:
            try:
                user_info_url = 'https://api.vk.com/method/users.get'
                params = {
                    'access_token': session.get('vk_token'),
                    'user_ids': user_id,
                    'fields': 'photo_200',
                    'v': '5.199'
                }
                
                response = requests.get(user_info_url, params=params)
                data = response.json()
                
                if 'response' in data and data['response']:
                    return data['response'][0].get('photo_200', '')
            except:
                pass
        return ''

    return dict(
        is_admin=check_is_admin,
        can_edit_admins=check_can_edit_admins,
        get_vk_user_photo=get_vk_user_photo
    )

@app.route('/')
def index():
    user_id = session.get('user_id')
    user_data = None
    if user_id:
        user_data = get_user_by_id(user_id)
    return render_template('index.html', user=user_data, user_id=user_id)

@app.route('/login', methods=['GET'])
def login():
    """Страница входа через VK ID"""
    # Если уже авторизован - на dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    # Генерируем nonce для CSP (если нужно)
    import secrets
    csp_nonce = secrets.token_hex(16)
    
    return render_template('login.html', csp_nonce=csp_nonce)
import requests

import base64
import hashlib
import hmac
CLIENT_SECRET = "xEbpCw780PwGn5PRw9jC"



def check_login_status():
    """API для проверки статуса логина"""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'No user_id'})
    
    status = 'not_found'
    if str(user_id) in database_login:
        status = database_login[str(user_id)].get('status', 'pending')
    
    print(f"[CHECK STATUS] User {user_id}: {status}")
    return jsonify({'status': status, 'user_id': user_id})
@app.route('/auto_login')
def auto_login():
    """Автоматический вход по токену"""
    user_id = request.args.get('user_id')
    token = request.args.get('token')
    
    print(f"[AUTO LOGIN] Попытка входа для {user_id} с токеном {token}")
    
    if not user_id or not token:
        flash('Неверная ссылка для входа', 'error')
        return redirect(url_for('login'))
    
    # Проверяем токен
    user_data = database_login.get(str(user_id))
    if user_data and user_data.get('login_token') == token:
        # Получаем данные пользователя
        user_info = get_user_by_id(user_id)
        
        if user_info:
            # Сохраняем в сессию
            session['user_id'] = user_id
            session.permanent = True
            
            # Очищаем временные данные
            del database_login[str(user_id)]
            
            flash(f'✅ Добро пожаловать, {user_info.get("username", user_id)}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Пользователь не найден в базе', 'error')
    else:
        flash('Неверный или устаревший токен входа', 'error')
    
    return redirect(url_for('login'))
@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        flash('Сначала авторизуйтесь!', 'error')
        return redirect(url_for('login'))

    user_data = get_user_by_id(user_id)
    if not user_data:
        session.clear()
        flash('Пользователь не найден!', 'error')
        return redirect(url_for('login'))

    return render_template('dashboard.html',
                         user=user_data,
                         packages=DONATE_PACKAGES)

@app.route('/garage')
def garage():
    user_id = session.get('user_id')
    if not user_id:
        flash('Сначала авторизуйтесь!', 'error')
        return redirect(url_for('login'))

    user_data = get_user_by_id(user_id)
    if not user_data:
        session.clear()
        flash('Пользователь не найден!', 'error')
        return redirect(url_for('login'))

    cars = user_data.get('cars', {})
    car_colors = get_car_colors(user_id)

    return render_template('garage.html',
                         user=user_data,
                         cars=cars,
                         car_colors=car_colors,
                         colors=CAR_COLORS)

@app.route('/buy_money')
def buy_money():
    user_id = session.get('user_id')
    if not user_id:
        flash('Сначала авторизуйтесь!', 'error')
        return redirect(url_for('login'))

    return render_template('buy_money.html')

@app.route('/calculate_money_price', methods=['POST'])
def calculate_money_price():
    try:
        requested_money = int(request.form.get('money_amount', 0))

        if requested_money <= 0:
            return jsonify({'success': False, 'error': 'Введите сумму больше 0'})

        COURSE = 50
        price = max(1, round(requested_money / COURSE))

        return jsonify({
            'success': True,
            'requested_money': requested_money,
            'price': price,
            'course': f"1₽ = {COURSE}₽"
        })

    except ValueError:
        return jsonify({'success': False, 'error': 'Введите корректное число'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/create_money_payment', methods=['POST'])
def create_money_payment():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Не авторизован'})

        requested_money = int(request.form.get('money_amount', 0))
        price = int(request.form.get('price', 0))

        if requested_money <= 0 or price <= 0:
            return jsonify({'success': False, 'error': 'Неверная сумма'})

        custom_package = {
            "name": f"Покупка {requested_money}₽",
            "price": price,
            "money": requested_money,
            "cars": [],
            "description": f"Покупка игровых денег"
        }

        payment_id = f"money_{user_id}_{requested_money}_{int(time.time())}"

        quickpay = Quickpay(
            receiver=YOOMONEY_RECEIVER,
            quickpay_form="shop",
            targets=f"Донат: {custom_package['name']}",
            paymentType="SB",
            sum=price,
            label=payment_id,
            successURL="https://racebotvk.pythonanywhere.com/payment_success"
        )

        payments_data = load_payments()
        payments_data['payments'][payment_id] = {
            "user_id": user_id,
            "package_type": "money_custom",
            "custom_money": requested_money,
            "amount": price,
            "status": "pending",
            "created_at": datetime.datetime.now().isoformat(),
            "payment_url": quickpay.base_url,
            "applied": False
        }
        save_payments(payments_data)

        session['current_payment'] = payment_id

        return jsonify({
            'success': True,
            'payment_url': quickpay.redirected_url
        })

    except Exception as e:
        print(f"Ошибка создания платежа для денег: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/buy_package/<package_type>')
def buy_package(package_type):
    try:
        print(f"Начало покупки пакета: {package_type}")

        user_id = session.get('user_id')
        if not user_id:
            flash('Сначала авторизуйтесь!', 'error')
            return redirect(url_for('login'))

        print(f"Пользователь: {user_id}")

        if package_type not in DONATE_PACKAGES:
            flash('Неверный тип набора!', 'error')
            return redirect(url_for('dashboard'))

        package = DONATE_PACKAGES[package_type]
        print(f"Пакет найден: {package['name']}")

        payment_id = f"{user_id}_{package_type}_{int(time.time())}"

        quickpay = Quickpay(
            receiver=YOOMONEY_RECEIVER,
            quickpay_form="shop",
            targets=f"Донат: {package['name']}",
            paymentType="SB",
            sum=package['price'],
            label=payment_id,
            successURL="https://racebotvk.pythonanywhere.com/payment_success"
        )

        payments_data = load_payments()
        payments_data['payments'][payment_id] = {
            "user_id": user_id,
            "package_type": package_type,
            "amount": package['price'],
            "status": "pending",
            "created_at": datetime.datetime.now().isoformat(),
            "payment_url": quickpay.base_url,
            "applied": False
        }
        save_payments(payments_data)

        session['current_payment'] = payment_id

        return redirect(quickpay.redirected_url)

    except Exception as e:
        print(f"Ошибка в buy_package: {str(e)}")
        import traceback
        print(f"Трассировка: {traceback.format_exc()}")
        flash(f'Ошибка при создании платежа: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/payment_success', methods=['GET'])
def payment_success():
    try:
        payment_id = session.get('current_payment')

        if not payment_id:
            flash('Информация о платеже не найдена.', 'info')
            return redirect(url_for('dashboard'))

        payments_data = load_payments()
        payment_info = payments_data['payments'].get(payment_id)

        if not payment_info:
            flash('Платеж не найден в базе.', 'warning')
            return redirect(url_for('dashboard'))

        if not payment_info.get('applied', False):
            user_data = get_user_by_id(payment_info['user_id'])
            
            if payment_info['package_type'] == 'money_custom':
                user_data['money'] += payment_info.get('custom_money', 0)
                message = f"Начислено {payment_info.get('custom_money', 0)} игровых рублей!"
            else:
                package = DONATE_PACKAGES.get(payment_info['package_type'])
                if package:
                    user_data['money'] += package['money']
                    message = f"Пакет '{package['name']}' применен! +{package['money']}₽"
                else:
                    message = "Пакет применен!"

            update_user_data(payment_info['user_id'], user_data)
            
            payment_info['status'] = 'completed'
            payment_info['applied'] = True
            payment_info['completed_at'] = datetime.datetime.now().isoformat()
            payments_data['payments'][payment_id] = payment_info
            save_payments(payments_data)

            flash(f'✅ {message}', 'success')
        else:
            flash('✅ Пакет уже был применен ранее!', 'info')

        session.pop('current_payment', None)
        return render_template('payment_success.html')

    except Exception as e:
        print(f"Ошибка в payment_success: {e}")
        flash('✅ Оплата прошла успешно! Бонусы будут начислены автоматически.', 'success')
        return render_template('payment_success.html')

@app.route('/payment_failed')
def payment_failed():
    flash('Оплата не была завершена. Попробуйте еще раз.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/payment_webhook', methods=['POST'])
def payment_webhook():
    try:
        data = request.form
        operation_id = data.get('operation_id')
        label = data.get('label')
        amount = data.get('amount')
        status = data.get('status')

        print(f"Webhook received: {label} - {status} - {amount}")

        if status == 'success' and label:
            payments_data = load_payments()
            payment_info = payments_data['payments'].get(label)

            if payment_info and payment_info['status'] != 'completed':
                user_data = get_user_by_id(payment_info['user_id'])
                
                if payment_info['package_type'] == 'money_custom':
                    user_data['money'] += payment_info.get('custom_money', 0)
                else:
                    package = DONATE_PACKAGES.get(payment_info['package_type'])
                    if package:
                        user_data['money'] += package['money']

                update_user_data(payment_info['user_id'], user_data)
                
                payment_info['status'] = 'completed'
                payment_info['completed_at'] = datetime.datetime.now().isoformat()
                payment_info['operation_id'] = operation_id
                payments_data['payments'][label] = payment_info
                save_payments(payments_data)

                print(f"Платеж {label} обработан успешно")

        return 'OK', 200

    except Exception as e:
        print(f"Ошибка в вебхуке: {e}")
        return 'Error', 500

@app.route('/check_payment_status')
def check_payment_status():
    payment_id = session.get('current_payment')

    if not payment_id:
        return jsonify({'status': 'error', 'message': 'Платеж не найден'})

    payments_data = load_payments()
    payment_info = payments_data['payments'].get(payment_id)

    if not payment_info:
        return jsonify({'status': 'error', 'message': 'Платеж не найден в базе'})

    if payment_info.get('applied', False):
        return jsonify({'status': 'completed'})

    try:
        client = Client(YOOMONEY_SECRET)
        history = client.operation_history(label=payment_id)

        for operation in history.operations:
            if operation.status == "success":
                user_data = get_user_by_id(payment_info['user_id'])
                
                if payment_info['package_type'] == 'money_custom':
                    user_data['money'] += payment_info.get('custom_money', 0)
                else:
                    package = DONATE_PACKAGES.get(payment_info['package_type'])
                    if package:
                        user_data['money'] += package['money']

                update_user_data(payment_info['user_id'], user_data)
                
                payment_info['status'] = 'completed'
                payment_info['applied'] = True
                payment_info['completed_at'] = datetime.datetime.now().isoformat()
                payments_data['payments'][payment_id] = payment_info
                save_payments(payments_data)
                
                return jsonify({'status': 'success'})
    except:
        pass

    return jsonify({'status': 'pending'})

@app.route('/update_car_color', methods=['POST'])
def update_car_color():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'})

    car_id = request.form.get('car_id')
    color = request.form.get('color')

    if not car_id or not color:
        return jsonify({'success': False, 'error': 'Неверные данные'})

    save_car_color(user_id, car_id, color)
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы успешно вышли из системы!', 'success')
    return redirect(url_for('index'))

# =============================================================================
# АДМИН-ФУНКЦИИ И РОУТЫ
# =============================================================================

import requests
from functools import wraps

def load_admin_data():
    try:
        with open('admin.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"moders": {"users_ids": []}}

def save_admin_data(data):
    with open('admin.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(user_id):
    try:
        admin_data = load_admin_data()
        user_id_str = str(user_id)
        return user_id_str in admin_data.get('moders', {}).get('users_ids', [])
    except Exception as e:
        print(f"Ошибка проверки админа: {e}")
        return False

def get_admin_permissions(user_id):
    admin_data = load_admin_data()
    user_data = admin_data.get('moders', {}).get(str(user_id), {})
    return user_data.get('perm', [])

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id or not is_admin(user_id):
            flash('Доступ запрещен!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def can_edit_admins(user_id):
    return str(user_id) == "819016396" or "can_admins_edit" in get_admin_permissions(user_id)

def get_vk_user_info(user_id):
    try:
        url = f"https://api.vk.com/method/users.get"
        params = {
            'user_ids': user_id,
            'fields': 'photo_200,first_name,last_name',
            'access_token': token,
            'v': '5.199'
        }
        response = requests.get(url, params=params)
        data = response.json()

        if 'response' in data and data['response']:
            user = data['response'][0]
            return {
                'id': user['id'],
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'photo': user.get('photo_200', '')
            }
    except Exception as e:
        print(f"Ошибка получения информации о пользователе: {e}")

    return None

@app.route('/admin/search_users')
def search_users():
    if not is_admin(session.get('user_id')):
        return jsonify({'success': False, 'error': 'Доступ запрещен'})

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'success': False, 'error': 'Пустой запрос'})

    users_data = load_data(USERS_DB_FILE)
    results = []
    
    for user_id, user_data in users_data.get('users', {}).items():
        if query.lower() in user_data.get('username', '').lower() or query == str(user_id):
            vk_info = get_vk_user_info(user_id)
            user_data['vk_info'] = vk_info
            user_data['id'] = user_id
            results.append(user_data)
    
    return jsonify({'success': True, 'users': results})

@app.route('/admin/login', methods=['GET', 'POST'])
@admin_required
def admin_login():
    if request.method == 'POST':
        secret_code = request.form.get('secret_code')
        user_id = session.get('user_id')

        expected_code = f"gonka_bot_admin_{user_id}"

        if secret_code == expected_code:
            session['admin_authenticated'] = True
            flash('Успешный вход в админ-панель!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Неверный секретный код!', 'error')

    return render_template('admin_login.html')

@app.route('/admin')
@admin_required
def admin_dashboard():
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))

    return render_template('admin_dashboard.html')

@app.route('/admin/users')
@admin_required
def admin_users():
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))

    users_data = load_data(USERS_DB_FILE)
    admin_data = load_admin_data()

    users_with_info = []
    for user_id, user_data in users_data.get('users', {}).items():
        vk_info = get_vk_user_info(user_id)
        if vk_info:
            user_data['vk_info'] = vk_info
            user_data['is_banned'] = user_id in admin_data.get('ban', {}).get('users_ids', [])
            user_data['id'] = user_id
            users_with_info.append(user_data)

    return render_template('admin_users.html', users=users_with_info)

@app.route('/admin/user/<user_id>')
@admin_required
def admin_user_detail(user_id):
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))

    users_data = load_data(USERS_DB_FILE)
    admin_data = load_admin_data()

    user_data = users_data.get('users', {}).get(user_id)
    if not user_data:
        flash('Пользователь не найден!', 'error')
        return redirect(url_for('admin_users'))

    vk_info = get_vk_user_info(user_id)
    ban_info = admin_data.get('ban', {}).get(user_id)

    return render_template('admin_user_detail.html',
                         user=user_data,
                         user_id=user_id,
                         vk_info=vk_info,
                         ban_info=ban_info)

@app.route('/admin/update_user_field', methods=['POST'])
@admin_required
def admin_update_user_field():
    try:
        user_id = request.form.get('user_id')
        field = request.form.get('field')
        value = request.form.get('value')

        users_data = load_data(USERS_DB_FILE)

        if user_id not in users_data.get('users', {}):
            return jsonify({'success': False, 'error': 'Пользователь не найден'})

        if field in ['money', 'exp', 'level', 'pistons']:
            value = int(value)
        elif field in ['cars', 'car_colors']:
            try:
                value = json.loads(value)
            except:
                return jsonify({'success': False, 'error': 'Неверный формат данных'})

        users_data['users'][user_id][field] = value
        save_data(users_data, USERS_DB_FILE)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/ban_user', methods=['POST'])
@admin_required
def admin_ban_user():
    try:
        user_id = request.form.get('user_id')
        days = int(request.form.get('days', 1))
        reason = request.form.get('reason', '')

        admin_data = load_admin_data()

        if 'ban' not in admin_data:
            admin_data['ban'] = {'users_ids': []}

        admin_data['ban']['users_ids'].append(user_id)
        admin_data['ban'][user_id] = {
            'days': days,
            'time': int(time.time()),
            'reason': reason
        }

        save_admin_data(admin_data)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/unban_user', methods=['POST'])
@admin_required
def admin_unban_user():
    try:
        user_id = request.form.get('user_id')

        admin_data = load_admin_data()

        if user_id in admin_data.get('ban', {}).get('users_ids', []):
            admin_data['ban']['users_ids'].remove(user_id)
            if user_id in admin_data['ban']:
                del admin_data['ban'][user_id]

            save_admin_data(admin_data)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/make_admin', methods=['POST'])
@admin_required
def admin_make_admin():
    try:
        target_user_id = request.form.get('user_id')
        role = request.form.get('role', 'moder')

        current_user_id = session.get('user_id')
        if not can_edit_admins(current_user_id):
            return jsonify({'success': False, 'error': 'Недостаточно прав'})

        admin_data = load_admin_data()

        if 'moders' not in admin_data:
            admin_data['moders'] = {'users_ids': []}

        if target_user_id not in admin_data['moders']['users_ids']:
            admin_data['moders']['users_ids'].append(target_user_id)

        admin_data['moders'][target_user_id] = {
            'status': role,
            'reports': 0,
            'perm': ['basic']
        }

        save_admin_data(admin_data)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/broadcast')
@admin_required
def admin_broadcast():
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))

    return render_template('admin_broadcast.html')

@app.route('/admin/send_broadcast', methods=['POST'])
@admin_required
def admin_send_broadcast():
    try:
        message = request.form.get('message')

        if not message:
            return jsonify({'success': False, 'error': 'Введите сообщение'})

        chats_data = load_data("chats.json")
        success_count = 0

        for chat_id, chat_info in chats_data.get('chats', {}).items():
            try:
                chat_message = Message({
                    'from_id': session.get('user_id'),
                    'peer_id': int(chat_id)
                }, vk)

                result = chat_message.reply(f"📢 РАССЫЛКА:\n\n{message}\n\n— Администрация")
                if result:
                    success_count += 1

                time.sleep(0.2)
            except:
                pass

        return jsonify({'success': True, 'sent_count': success_count})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/admins')
@admin_required
def admin_admins():
    if not session.get('admin_authenticated'):
        return redirect(url_for('admin_login'))

    current_user_id = session.get('user_id')
    if not can_edit_admins(current_user_id):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('admin_dashboard'))

    admin_data = load_admin_data()
    moderators = admin_data.get('moders', {})

    admins_with_info = []
    for user_id in moderators.get('users_ids', []):
        if user_id in moderators:
            vk_info = get_vk_user_info(user_id)
            if vk_info:
                admin_info = moderators[user_id]
                admin_info['vk_info'] = vk_info
                admin_info['id'] = user_id
                admins_with_info.append(admin_info)

    return render_template('admin_admins.html', admins=admins_with_info)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    flash('Вы вышли из админ-панели', 'info')
    return redirect(url_for('dashboard'))

# =============================================================================
# ФУНКЦИИ ОБРАБОТКИ СООБЩЕНИЙ VK (из вашего кода)
# =============================================================================

def handle_message_event(message_data):
    """Обработка новых сообщений (скопировано из вашего кода)"""
    message = Message(message_data, vk)
    text = message.text.lower()

    # Обработка payload для обычных кнопок
    payload = None
    try:
        if 'payload' in message_data and message_data['payload']:
            payload = json.loads(message_data['payload'])
    except (KeyError, json.JSONDecodeError, TypeError):
        pass

    # Если есть payload - обрабатываем команду из кнопки
    if payload and 'cmd' in payload:
        handle_button_command(message, payload['cmd'], payload)
        return

    # Обработка текстовых команд
    if text in ["меню", "/start", "start", "начать"]:
        show_menu(message)
    elif text in ["работы", "работа", "job", "jobs"]:
        show_jobs_menu(message)
    elif text.startswith("работа автомеханик"):
        start_job_mechanic(message)
    elif text.startswith("работа таксист"):
        start_job_taxi(message)
    elif text == "статистика работ":
        show_job_stats(message)
    elif text in ['помощь', 'команды', 'help']:
        show_commands(message)
    elif text in ['гонка', 'гонки', 'race']:
        if message.from_id != message.peer_id:
            show_races(message)
    elif text in ["pvp", "пвп", "гонка пвп"]:
        handle_pvp_command(message)
    elif text in ["старт", "начать гонку"]:
        start_race(message)
    elif text in ["гараж", "garage"]:
        show_garage(message)
    elif text in ["автосалон", "магазин", "shop"]:
        show_cars_shop(message)
    elif text in ["техцентр", "сервис", "service"]:
        show_service(message)
    elif text in ["глобальные гонки", "глобальные", "global"]:
        show_global_races(message)
    elif text in ["мои результаты", "статистика", "stats"]:
        my_results(message)
    elif text in ["выйти из гонки", "покинуть гонку"]:
        leave_race(message)

    elif text == "мой айди":
        if message.from_id != message.peer_id:
            message.reply("Данная команда доступна только в лс бота!")
        else:
            message.reply(message.from_id)
    elif text == "поддержка":
        message.reply("Если у вас возникли какие-то проблемы, обращайтесь к - @deniska_bisekeev")
    elif text == "вход":
        user_id = message.from_id
        if str(user_id) not in database_login:
            message.reply("Вы не пытаетесь войти в данный момент на сайт!")
            pass
        message.reply("Согласие дано, напишите заново свой айди в форме, чтобы войти..")
        database_login[str(user_id)]['status'] = 'success'
    elif text == "донат":
        keyboard = VkKeyboard(inline=True)
        keyboard.add_openlink_button("Перейти на сайт", "https://racebotvk.pythonanywhere.com")
        t = f"Привет, {message.get_mention(message.from_id)}, чтобы оплатить донат, перейдите на наш сайт. При входе вас попросят написать ваш айди, перейдите в лс бота - [vk.me/gonka_bot|тык] и напишите 'мой айди'"
        message.reply(t, keyboard=keyboard.get_keyboard())
    elif text.startswith("клан"):
        args = text.split()[1:]
        handle_klan_command(message, args)
    elif text.startswith("битва присоединиться"):
        join_klan_battle(message, text.split()[2])
    elif text.startswith("драг"):
        handle_drag_race(message)
    elif text.startswith("/admin"):
        data = load_data('admin.json')
        if str(message.from_id) in data['moders']['users_ids']:
            args = text.split()
            handle_admin_command(message, args)
        else:
            None
    elif text == "айди чата":
        message.reply(message.peer_id)
    elif text.startswith("рассылка"):
        admin_ids = admins_ids

        if message.from_id not in admin_ids:
            return message.reply("❌ У вас нет прав для рассылки!")

        broadcast_text = text[9:].strip()

        if not broadcast_text:
            return message.reply("❌ Укажите текст для рассылки!\nПример: рассылка Привет всем!")

        formatted_text = f"📢 РАССЫЛКА ОТ АДМИНИСТРАЦИИ:\n\n{broadcast_text}\n\n— Бот Гонки"

        db = load_data("chats.json")
        chats_data = db.get('chats', {})

        if not chats_data:
            return message.reply("❌ Нет чатов в базе данных!")

        message.reply(f"🚀 Начинаю рассылку в {len(chats_data)} чатов...")

        success_count = 0
        error_count = 0
        error_list = []

        for chat_id, chat_info in chats_data.items():
            try:
                chat_message = Message({
                    'from_id': message.from_id,
                    'peer_id': int(chat_id)
                }, vk)

                result = chat_message.reply(formatted_text)

                if result:
                    success_count += 1
                else:
                    error_count += 1
                    error_list.append(f"{chat_info.get('title', 'Без названия')} (ID: {chat_id})")

                time.sleep(0.2)

            except Exception as e:
                error_count += 1
                error_list.append(f"{chat_info.get('title', 'Без названия')} (ID: {chat_id}) - {str(e)}")
                print(f"❌ Ошибка в чате {chat_id}: {e}")

        report = (
            f"📊 РАССЫЛКА ЗАВЕРШЕНА:\n\n"
            f"✅ Успешно: {success_count}\n"
            f"❌ Ошибок: {error_count}\n"
            f"📝 Всего чатов: {len(chats_data)}"
        )

        if error_list:
            report += f"\n\nПоследние ошибки:\n" + "\n".join(error_list[:5])
            if len(error_list) > 5:
                report += f"\n... и ещё {len(error_list) - 5} ошибок"

        message.reply(report)
    else:
        unknow_command(message)

def handle_callback_event(event_data):
    """Обработка callback кнопок"""
    try:
        user_id = event_data['user_id']
        peer_id = event_data['peer_id']
        cmd = event_data.get('payload', {}).get('cmd')
        
        print(f"[CALLBACK] Получен callback: {cmd} от пользователя {user_id}")
        
        # ВАЖНО: Сначала подтверждаем callback
        try:
            vk.messages.sendMessageEventAnswer(
                event_id=event_data['event_id'],
                user_id=user_id,
                peer_id=peer_id,
                event_data=json.dumps({"type": "show_snackbar", "text": "✅ Обработано"})
            )
            print(f"[CALLBACK] Callback подтвержден для {user_id}")
        except Exception as e:
            print(f"[CALLBACK] Ошибка подтверждения: {e}")
        
        # Теперь обрабатываем команду
        if cmd == 'join_race':
            # Создаем объект сообщения
            message_data = {
                'from_id': user_id,
                'peer_id': peer_id,
                'payload': event_data.get('payload', {}),
                'conversation_message_id': event_data.get('conversation_message_id')
            }
            message = Message(message_data, vk)
            join_race(message)
            
        elif cmd == 'leave_race':
            message_data = {
                'from_id': user_id,
                'peer_id': peer_id,
                'payload': event_data.get('payload', {}),
                'conversation_message_id': event_data.get('conversation_message_id')
            }
            message = Message(message_data, vk)
            leave_race(message)
            
        elif cmd == 'login':
            print(f"[LOGIN CALLBACK] Пользователь {user_id} подтверждает вход")
            
            # Проверяем есть ли запрос
            if str(user_id) in database_login:
                # Меняем статус
                database_login[str(user_id)]['status'] = 'success'
                print(f"[LOGIN CALLBACK] Статус изменен для {user_id}")
                
                # Создаем уникальный токен для автоматического входа
                import secrets
                login_token = secrets.token_urlsafe(32)
                database_login[str(user_id)]['login_token'] = login_token
                
                # Отправляем пользователю ссылку для автоматического входа
                try:
                    # Получаем URL сайта (для Cloud Shell)
                    import socket
                    hostname = socket.gethostname()
                    site_url = f"https://8080-cs-23e077d0-803a-4897-be90-adc75f98d8a5.cs-europe-west4-bhnf.cloudshell.dev/"
                    
                    login_url = f"{site_url}/auto_login?user_id={user_id}&token={login_token}"
                    
                    vk.messages.send(
                        user_id=user_id,
                        message=f"✅ Вход подтвержден!\n\n"
                               f"Для автоматического входа нажмите ссылку:\n"
                               f"{login_url}\n\n"
                               f"Или перейдите на сайт и введите ваш ID еще раз.",
                        random_id=0
                    )
                    print(f"[LOGIN CALLBACK] Сообщение с ссылкой отправлено")
                    
                except Exception as e:
                    print(f"[LOGIN CALLBACK] Ошибка отправки: {e}")
                    # Альтернативное сообщение
                    try:
                        vk.messages.send(
                            user_id=user_id,
                            message=f"✅ Вход подтвержден!\n\n"
                                   f"Теперь вернитесь на сайт и введите ваш ID: {user_id}",
                            random_id=0
                        )
                    except:
                        pass
            else:
                print(f"[LOGIN CALLBACK] Пользователь {user_id} не найден в ожидающих")
        
        else:
            print(f"[CALLBACK] Неизвестная команда: {cmd}")
            
    except Exception as e:
        print(f"[CALLBACK] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

def check_login(user_id):
    """Удаление данных логина через 5 минут"""
    time.sleep(300)  # 5 минут
    try:
        if str(user_id) in database_login:
            del database_login[str(user_id)]
            print(f"[LOGIN] Данные логина для {user_id} очищены (таймаут 5 минут)")
    except:
        pass

def handle_button_command(message, cmd, payload):
    """Обработка команд из обычных кнопок"""
    if cmd == 'garage':
        show_garage(message)
    elif cmd == 'cars_shop':
        show_cars_shop(message)
    elif cmd == 'service':
        show_service(message)
    elif cmd == 'global_races':
        show_global_races(message)
    elif cmd == 'buy_car':
        buy_car(message, payload.get('car_id'))
    elif cmd == 'repair_tires':
        repair_tires(message)
    elif cmd == 'repair_body':
        repair_body(message)
    elif cmd == 'upgrade_engine':
        upgrade_engine(message)
    elif cmd == 'upgrade_speed':
        upgrade_speed(message)
    elif cmd == 'select_car':
        select_car(message)
    elif cmd == 'set_active_car':
        set_active_car(message, payload.get('car_id'))
    elif cmd == 'create_race':
        create_race(message)
    elif cmd == 'start_race':
        start_race(message)
    elif cmd == 'race_status':
        show_race_status(message)
    elif cmd == 'find_global_race':
        find_global_race(message)
    elif cmd == 'my_results':
        my_results(message)
    elif cmd == 'accept_drag':
        accept_drag_race(message, payload.get('drag_id'))
    elif cmd == 'decline_drag':
        message.reply("❌ Вызов на драг-рейсинг отклонен.")
    elif cmd == 'pvp_race':
        handle_pvp_command(message)
    elif cmd == 'klan_create_menu':
        message.reply("Для создания клана используйте команду:\nклан создать [название] [тег]\n\nПример: клан создать ГонщикиПро GP")
    elif cmd == 'klan_info':
        show_klan_info(message)
    elif cmd == 'klan_members':
        show_klan_members(message)
    elif cmd == 'klan_battle':
        start_klan_battle(message)
    elif cmd == 'klan_invite_menu':
        message.reply("Для приглашения в клан используйте команду:\nклан приглос [@игрок]\n\nПример: клан приглос @username")
    elif cmd == 'klan_accept':
        accept_klan_invite(message, [payload.get('invite_id')])
    elif cmd == 'klan_decline':
        message.reply("❌ Приглашение в клан отклонено.")
    elif cmd == 'klan_top':
        show_klan_top(message)

# =============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =============================================================================

def start_bot_thread():
    """Запустить бота в отдельном потоке"""
    global bot_thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("🤖 Бот VK запущен в отдельном потоке")

if __name__ == '__main__':
    # Инициализируем бота
    init_bot()
    
    # Запускаем бота в отдельном потоке
    start_bot_thread()

    # Запускаем авто-перезапуск
    auto_restart.start()
    
    # Запускаем Flask приложение
    print("🌐 Веб-сайт запущен по адресу: http://localhost:7000")
    print("📱 Бот VK работает через LongPoll")
    app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)
