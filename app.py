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
longpoll = None
bot_thread = None

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
# VK БОТ
# =============================================================================

def init_bot():
    """Инициализировать бота"""
    global longpoll, vk_session, vk
    try:
        vk_session = vk_api.VkApi(token=token)
        vk = vk_session.get_api()
        longpoll = VkBotLongPoll(vk_session, GROUP_ID)
        print("✅ VK бот инициализирован")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации бота: {e}")
        return False

def run_bot():
    """Запустить бота"""
    print("🚀 Запуск бота VK...")
    
    while True:
        try:
            if not longpoll:
                if not init_bot():
                    time.sleep(10)
                    continue
            
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
        message_data = {
            'from_id': event.obj.message['from_id'],
            'peer_id': event.obj.message['peer_id'],
            'text': event.obj.message['text'],
            'conversation_message_id': event.obj.message.get('conversation_message_id'),
            'id': event.obj.message.get('id'),
        }
        
        if 'payload' in event.obj.message and event.obj.message['payload']:
            message_data['payload'] = event.obj.message['payload']
        
        message = Message(message_data, vk)
        text = event.obj.message['text'].lower() if event.obj.message['text'] else ""
        
        if 'payload' in event.obj.message and event.obj.message['payload']:
            try:
                payload = json.loads(event.obj.message['payload'])
                if 'cmd' in payload:
                    handle_button_command(message, payload['cmd'], payload)
                    return
            except:
                pass

        if event.obj.message.get('action'):
            action_type = event.obj.message['action']['type']
            if action_type == 'chat_invite_user':
                new_member_id = event.obj.message['action']['member_id']
                if new_member_id == -int(GROUP_ID):
                    send_welcome_message(event)
                    return
        
        handle_message_event(message_data)
        
    except Exception as e:
        print(f"❌ Ошибка обработки сообщения: {e}")

def send_welcome_message(event):
    """Отправка приветственного сообщения"""
    try:
        chat_id = event.obj.message['chat_id']
        
        welcome_text = """@all 🏎️ ДОБРО ПОЖАЛОВАТЬ В ГОНОЧНЫЙ БОТ!

Приветствую всех участников чата! 🎉

Я — бот для организации захватывающих гонок и соревнований.

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
Для доступа к полному функционалу напишите мне в личные сообщения:
[vk.me/gonka_bot|Написать боту]

🎮 Удачи на треках! 🏁"""

        keyboard = VkKeyboard(inline=True)
        keyboard.add_button("🏎️ Создать гонку", VkKeyboardColor.POSITIVE, payload={'cmd': 'create_race'})
        keyboard.add_line()
        keyboard.add_button("📋 Команды", VkKeyboardColor.PRIMARY, payload={'cmd': 'show_commands'})
        
        vk.messages.send(
            peer_id=event.obj['peer_id'],
            message=welcome_text,
            keyboard=keyboard.get_keyboard(),
            random_id=0
        )
        
    except Exception as e:
        print(f"❌ Ошибка отправки приветствия: {e}")

def handle_vk_callback(event):
    """Обработка callback кнопок VK"""
    try:
        message_data = {
            'from_id': event.object['user_id'],
            'user_id': event.object['user_id'],
            'peer_id': event.object['peer_id'],
            'payload': event.object.get('payload'),
            'conversation_message_id': event.object.get('conversation_message_id')
        }
        
        message = Message(message_data, vk)
        handle_callback_event(message_data)
        
    except Exception as e:
        print(f"❌ Ошибка обработки callback: {e}")

# =============================================================================
# FLASK РОУТЫ
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
            successURL=f"{request.host_url}payment_success"
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
            successURL=f"{request.host_url}payment_success"
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

@app.route('/payment_webhook', methods=['POST'])
def payment_webhook():
    try:
        data = request.form
        operation_id = data.get('operation_id')
        label = data.get('label')
        amount = data.get('amount')
        status = data.get('status')
        
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
        
        return 'OK', 200
        
    except Exception as e:
        print(f"Ошибка в вебхуке: {e}")
        return 'Error', 500

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
        return str(user_id) in admin_data.get('moders', {}).get('users_ids', [])
    except Exception as e:
        print(f"Ошибка проверки админа: {e}")
        return False

@app.route('/admin')
def admin_dashboard():
    user_id = session.get('user_id')
    if not user_id or not is_admin(user_id):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('dashboard'))
    return render_template('admin_dashboard.html')

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
    port = int(os.environ.get("PORT", 5000))
    
    # Инициализация бота
    print("🤖 Инициализация VK бота...")
    if init_bot():
        start_bot_thread()
        print("✅ Бот VK запущен")
    else:
        print("⚠️ Бот VK не запущен, но веб-сайт работает")
    
    # Запуск Flask
    print(f"🌐 Запуск веб-сервера на порту {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
