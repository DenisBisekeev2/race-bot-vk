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
# WEBHOOK РОУТЫ ДЛЯ VK БОТА
# =============================================================================

@app.route('/vk-webhook', methods=['POST'])
def vk_webhook():
    """Основной вебхук для VK API"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'response': 'error', 'message': 'No JSON data'}), 400
        
        # Проверка типа события
        if data.get('type') == 'confirmation':
            # Возвращаем строку подтверждения для настройки вебхука
            return '9bb1bfa1'
        
        elif data.get('type') == 'message_new':
            # Обработка нового сообщения
            message_data = {
                'from_id': data['object']['message']['from_id'],
                'peer_id': data['object']['message']['peer_id'],
                'text': data['object']['message']['text'],
                'conversation_message_id': data['object']['message'].get('conversation_message_id'),
                'id': data['object']['message'].get('id'),
            }
            
            if 'payload' in data['object']['message'] and data['object']['message']['payload']:
                message_data['payload'] = data['object']['message']['payload']
            
            # Запускаем обработку в отдельном потоке
            threading.Thread(target=process_vk_message, args=(message_data,)).start()
            
            return jsonify({'response': 'ok'})
        
        elif data.get('type') == 'message_event':
            # Обработка callback кнопок
            event_data = {
                'user_id': data['object']['user_id'],
                'peer_id': data['object']['peer_id'],
                'event_id': data['object']['event_id'],
                'conversation_message_id': data['object']['conversation_message_id'],
                'payload': data['object']['payload']
            }
            
            # Запускаем обработку в отдельном потоке
            threading.Thread(target=process_vk_callback, args=(event_data,)).start()
            
            return jsonify({'response': 'ok'})
        
        else:
            return jsonify({'response': 'ok'})
            
    except Exception as e:
        print(f"❌ Ошибка в вебхуке: {e}")
        return jsonify({'response': 'error', 'message': str(e)}), 500

def process_vk_message(message_data):
    """Обработка сообщения VK в отдельном потоке"""
    try:
        message = Message(message_data, vk)
        text = message_data.get('text', '').lower()
        
        # Проверяем действие (action) для приветствия при добавлении бота
        if 'action' in message_data and message_data['action']:
            action_type = message_data['action'].get('type')
            if action_type == 'chat_invite_user':
                new_member_id = message_data['action'].get('member_id')
                if new_member_id == -int(GROUP_ID):
                    send_welcome_message(message)
                    return
        
        # Обработка payload для кнопок
        if 'payload' in message_data and message_data['payload']:
            try:
                payload = json.loads(message_data['payload'])
                if 'cmd' in payload:
                    handle_button_command(message, payload['cmd'], payload)
                    return
            except:
                pass
        
        # Обработка текстовых команд через существующую функцию
        handle_message_event(message_data)
        
    except Exception as e:
        print(f"❌ Ошибка обработки сообщения: {e}")

def process_vk_callback(event_data):
    """Обработка callback кнопок VK в отдельном потоке"""
    try:
        # Создаем структуру данных для совместимости
        message_data = {
            'from_id': event_data['user_id'],
            'user_id': event_data['user_id'],
            'peer_id': event_data['peer_id'],
            'payload': event_data.get('payload'),
            'conversation_message_id': event_data.get('conversation_message_id'),
            'event_id': event_data['event_id']
        }
        
        message = Message(message_data, vk)
        
        # Подтверждаем callback
        try:
            vk.messages.sendMessageEventAnswer(
                event_id=event_data['event_id'],
                user_id=event_data['user_id'],
                peer_id=event_data['peer_id'],
                event_data=json.dumps({"type": "show_snackbar", "text": "✅ Обработано"})
            )
        except Exception as e:
            print(f"❌ Ошибка подтверждения callback: {e}")
        
        # Обрабатываем callback
        handle_callback_event(message_data)
        
    except Exception as e:
        print(f"❌ Ошибка обработки callback: {e}")

def send_welcome_message(message):
    """Отправка приветственного сообщения при добавлении бота в чат"""
    try:
        peer_id = message.peer_id
        
        welcome_text = """@all 🏎️ ДОБРО ПОЖАЛОВАТЬ В ГОНОЧНЫЙ БОТ!

Приветствую всех участников чата! 🎉

Я — бот для организации захватывающих гонок и соревнований. Вот что я умею:

🚀 ОСНОВНЫЕ ВОЗМОЖНОСТИ:
• 🏎️ Создавать гонки прямо в чате
• 🚗 Покупать и улучшать автомобили
• ⚔️ Устраивать драг-рейсинг
• 🏆 Создавать кланы и битвы кланов
• 💼 Работать автомехаником или таксистом

📋 КОМАНДЫ ДЛЯ ЧАТА:
• "Гонка" - создать/присоединиться к гонке
• "Меню" - показать главное меню
• "Драг @игрок" - вызвать на драг-рейсинг
• "Клан" - система кланов

👤 ЛИЧНЫЕ СООБЩЕНИЯ:
Для доступа к полному функционалу (гараж, автосалон, техцентр, PvP гонки) напишите мне в личные сообщения:
[vk.me/gonka_bot|Написать боту]

🎮 Удачи на треках и пусть победит самый быстрый! 🏁

P.S. Для помощи напишите "Помощь"."""

        keyboard = VkKeyboard(inline=True)
        keyboard.add_button("🏎️ Создать гонку", VkKeyboardColor.POSITIVE, payload={'cmd': 'create_race'})
        keyboard.add_line()
        keyboard.add_button("📋 Команды", VkKeyboardColor.PRIMARY, payload={'cmd': 'show_commands'})
        
        vk.messages.send(
            peer_id=peer_id,
            message=welcome_text,
            keyboard=keyboard.get_keyboard(),
            random_id=0
        )
        
        print(f"✅ Приветственное сообщение отправлено в чат {peer_id}")
        
    except Exception as e:
        print(f"❌ Ошибка отправки приветствия: {e}")

def handle_callback_event(event_data):
    """Обработка callback событий"""
    try:
        user_id = event_data['user_id']
        payload = event_data.get('payload', {})
        cmd = payload.get('cmd') if isinstance(payload, dict) else json.loads(payload).get('cmd') if payload else None
        
        print(f"[CALLBACK] Получен callback: {cmd} от пользователя {user_id}")
        
        if cmd == 'join_race':
            message = Message(event_data, vk)
            join_race(message)
            
        elif cmd == 'leave_race':
            message = Message(event_data, vk)
            leave_race(message)
            
        elif cmd == 'login':
            print(f"[LOGIN CALLBACK] Пользователь {user_id} подтверждает вход")
            
            if str(user_id) in database_login:
                database_login[str(user_id)]['status'] = 'success'
                print(f"[LOGIN CALLBACK] Статус изменен для {user_id}")
                
                import secrets
                login_token = secrets.token_urlsafe(32)
                database_login[str(user_id)]['login_token'] = login_token
                
                try:
                    vk.messages.send(
                        user_id=user_id,
                        message=f"✅ Вход подтвержден!\n\n"
                               f"Теперь вернитесь на сайт и введите ваш ID: {user_id}",
                        random_id=0
                    )
                except Exception as e:
                    print(f"[LOGIN CALLBACK] Ошибка отправки: {e}")
                    
    except Exception as e:
        print(f"[CALLBACK] Ошибка: {e}")

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
# FLASK РОУТЫ ДЛЯ САЙТА
# =============================================================================

@app.route('/')
def index():
    user_id = session.get('user_id')
    user_data = None
    if user_id:
        user_data = get_user_by_id(user_id)
    return render_template('index.html', user=user_data, user_id=user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '').strip()
        
        try:
            db = load_data("users.json")
            
            if user_id and str(user_id) in db.get('users', {}):
                user_data = db['users'][str(user_id)]
                
                if 'site' in user_data and 'password' in user_data['site']:
                    if password == user_data['site']['password']:
                        session['user_id'] = user_id
                        flash('✅ Успешный вход!', 'success')
                        return redirect(url_for('dashboard'))
        except:
            flash('❌ Неверные данные', 'danger')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    
    if not user_id:
        flash('⚠️ Пожалуйста, войдите в систему', 'warning')
        return redirect(url_for('login'))
    
    try:
        db = load_data("users.json")
        
        if str(user_id) not in db.get('users', {}):
            session.clear()
            flash('⚠️ Пользователь не найден', 'danger')
            return redirect(url_for('login'))
        
        user_data = db['users'][str(user_id)]
        
        return render_template('dashboard.html', 
                             user=user_data,
                             user_id=user_id,
                             DONATE_PACKAGES=DONATE_PACKAGES)
    
    except Exception as e:
        flash(f'⚠️ Ошибка: {str(e)}', 'danger')
        return redirect(url_for('login'))

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
            successURL="https://racebotvk.onrender.com/payment_success"
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
        user_id = session.get('user_id')
        if not user_id:
            flash('Сначала авторизуйтесь!', 'error')
            return redirect(url_for('login'))
        
        if package_type not in DONATE_PACKAGES:
            flash('Неверный тип набора!', 'error')
            return redirect(url_for('dashboard'))
        
        package = DONATE_PACKAGES[package_type]
        payment_id = f"{user_id}_{package_type}_{int(time.time())}"
        
        quickpay = Quickpay(
            receiver=YOOMONEY_RECEIVER,
            quickpay_form="shop",
            targets=f"Донат: {package['name']}",
            paymentType="SB",
            sum=package['price'],
            label=payment_id,
            successURL="https://racebotvk.onrender.com/payment_success"
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
        from yoomoney import Client
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
# АДМИН ФУНКЦИИ
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
# ФУНКЦИИ ОБРАБОТКИ СООБЩЕНИЙ VK
# =============================================================================

def handle_message_event(message_data):
    """Обработка новых сообщений"""
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
    elif text == "сайт":
        show_site(message)
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
    elif text == "/db":
        handle_db_command(message)
    
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
        keyboard.add_openlink_button("Перейти на сайт", "https://racebotvk.onrender.com")
        t = f"Привет, {message.get_mention(message.from_id)}, чтобы оплатить донат, перейдите на наш сайт. При входе вас попросят написать ваш айди, перейдите в лс бота - [vk.me/gonka_bot|тык] и напишите 'мой айди'"
        message.reply(t, keyboard=keyboard.get_keyboard())
    elif text.startswith("клан"):
        args = text.split()[1:]
        handle_klan_command(message, args)
    elif text.startswith("битва присоединиться"):
        join_klan_battle(message, text.split()[2])
    elif text.startswith("драг"):
        handle_drag_race(message)
    elif text in ["бэкап", "/бэкап", "backup"]:
        handle_backup_command(message)
    elif text.startswith("/admin"):
        data = load_data('admin.json')
        if str(message.from_id) in data['moders']['users_ids']:
            args = text.split()
            handle_admin_command(message, args)
        else:
            None
    elif text in ["/github_sync", "синхронизировать", "сохранить на github"]:
        handle_github_sync_command(message)
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

def handle_github_sync_command(message):
    """Обработка команды синхронизации с GitHub"""
    # Проверяем права (только админы)
    db = load_data("admin.json")
    if str(message.from_id) not in db['moders']['users_ids']:
        return
    
    message.reply("🔄 Начинаю ручную синхронизацию с GitHub...")
    
    try:
        if github_sync:
            github_sync.manual_sync()
            message.reply("✅ Синхронизация завершена успешно!")
        else:
            message.reply("❌ GitHub синхронизация не инициализирована")
    except Exception as e:
        message.reply(f"❌ Ошибка синхронизации: {str(e)}")

def handle_button_command(message, cmd, payload):
    """Обработка команд из обычных кнопок"""
    
    if cmd == 'garage':
        show_garage(message)
    elif cmd == 'site_update':
        handle_password_update(message)
    elif cmd == 'jobs_menu':
        show_jobs_menu(message)
    elif cmd == "show_commands":
        show_commands(message)
    elif cmd == 'start_job':
        job_id = payload.get('job_id')
        if job_id == 'mechanic':
            start_job_mechanic(message)
        elif job_id == 'taxi':
            start_job_taxi(message)
    elif cmd == 'job_stats':
        show_job_stats(message)
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
# ДОПОЛНИТЕЛЬНЫЕ РОУТЫ
# =============================================================================

@app.route('/health')
def health_check():
    """Эндпоинт для проверки здоровья"""
    return 'OK', 200

@app.route('/keepalive')
def keepalive():
    """Эндпоинт для поддержания работы бота"""
    return 'Bot is alive', 200

@app.route('/auto_login')
def auto_login():
    """Автоматический вход по токену"""
    user_id = request.args.get('user_id')
    token_param = request.args.get('token')
    
    print(f"[AUTO LOGIN] Попытка входа для {user_id} с токеном {token_param}")
    
    if not user_id or not token_param:
        flash('Неверная ссылка для входа', 'error')
        return redirect(url_for('login'))
    
    # Проверяем токен
    user_data = database_login.get(str(user_id))
    if user_data and user_data.get('login_token') == token_param:
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

# =============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    
    print(f"🌐 Запуск веб-сервера на порту {port}...")
    print(f"🤖 ВК бот работает через вебхук: /vk-webhook")
    print(f"✅ Для настройки вебхука в VK укажите URL: https://racebotvk.onrender.com/vk-webhook")
    print(f"✅ Строка подтверждения: 9bb1bfa1")
    
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
