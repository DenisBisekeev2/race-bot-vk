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
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ САЙТА
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
# WEBHOOK ДЛЯ VK - ОСНОВНОЙ РОУТ
# =============================================================================

@app.route('/vk-webhook', methods=['POST', 'GET'])
def vk_webhook():
    """Вебхук для VK Callback API"""
    if request.method == 'GET':
        # Подтверждение вебхука
        return '9bb1bfa1'
    
    try:
        data = request.json
        
        if data.get('type') == 'confirmation':
            return '9bb1bfa1'
        
        elif data.get('type') == 'message_new':
            # Обработка нового сообщения
            message_obj = data['object']['message']
            message_data = {
                'from_id': message_obj['from_id'],
                'peer_id': message_obj['peer_id'],
                'text': message_obj.get('text', ''),
                'conversation_message_id': message_obj.get('conversation_message_id'),
                'id': message_obj.get('id'),
            }
            
            if 'payload' in message_obj and message_obj['payload']:
                message_data['payload'] = message_obj['payload']
            
            # Запускаем обработку в потоке
            threading.Thread(target=handle_webhook_message, args=(message_data,)).start()
            
        elif data.get('type') == 'message_event':
            # Обработка callback кнопок
            event_obj = data['object']
            event_data = {
                'user_id': event_obj['user_id'],
                'peer_id': event_obj['peer_id'],
                'event_id': event_obj['event_id'],
                'payload': event_obj['payload']
            }
            
            # Подтверждаем и обрабатываем
            threading.Thread(target=handle_webhook_callback, args=(event_data,)).start()
        
        # Всегда возвращаем 'ok' VK
        return jsonify({'response': 'ok'})
        
    except Exception as e:
        print(f"Ошибка в вебхуке: {e}")
        return jsonify({'response': 'ok'})

def handle_webhook_message(message_data):
    """Обработка сообщения из вебхука"""
    try:
        # Создаем сессию VK для этого потока
        local_vk_session = vk_api.VkApi(token=token)
        local_vk = local_vk_session.get_api()
        
        # Создаем объект Message
        message = Message(message_data, local_vk)
        
        # Проверяем action (добавление бота в чат)
        if 'action' in message_data and message_data['action']:
            action_type = message_data['action'].get('type')
            if action_type == 'chat_invite_user':
                new_member_id = message_data['action'].get('member_id')
                if new_member_id == -int(GROUP_ID):
                    # Отправляем приветственное сообщение
                    send_welcome_to_chat(message)
                    return
        
        # Проверяем payload (нажатие кнопки)
        if 'payload' in message_data and message_data['payload']:
            try:
                payload = json.loads(message_data['payload'])
                if 'cmd' in payload:
                    handle_button_command(message, payload['cmd'], payload)
                    return
            except:
                pass
        
        # Обработка текстовых команд
        process_text_command(message)
        
    except Exception as e:
        print(f"Ошибка обработки сообщения: {e}")

def handle_webhook_callback(event_data):
    """Обработка callback из вебхука"""
    try:
        # Создаем сессию VK
        local_vk_session = vk_api.VkApi(token=token)
        local_vk = local_vk_session.get_api()
        
        # Подтверждаем callback
        local_vk.messages.sendMessageEventAnswer(
            event_id=event_data['event_id'],
            user_id=event_data['user_id'],
            peer_id=event_data['peer_id'],
            event_data=json.dumps({"type": "show_snackbar", "text": "✅ Обработано"})
        )
        
        # Создаем структуру данных для обработки
        message_data = {
            'from_id': event_data['user_id'],
            'user_id': event_data['user_id'],
            'peer_id': event_data['peer_id'],
            'payload': event_data.get('payload'),
            'conversation_message_id': event_data.get('conversation_message_id')
        }
        
        message = Message(message_data, local_vk)
        
        # Обрабатываем callback
        handle_callback_event(message_data)
        
    except Exception as e:
        print(f"Ошибка обработки callback: {e}")

def send_welcome_to_chat(message):
    """Отправка приветствия при добавлении бота в чат"""
    try:
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
        
        vk.messages.send(
            peer_id=message.peer_id,
            message=welcome_text,
            keyboard=keyboard.get_keyboard(),
            random_id=int(time.time() * 1000)
        )
        
    except Exception as e:
        print(f"Ошибка отправки приветствия: {e}")

# =============================================================================
# ОБРАБОТЧИКИ КОМАНД (ИЗ ВАШЕГО ИСХОДНОГО КОДА)
# =============================================================================

def process_text_command(message):
    """Обработка текстовых команд"""
    text = message.text.lower() if message.text else ""
    
    # Проверяем импортированные функции
    if text in ["меню", "/start", "start", "начать"]:
        show_menu(message)
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
    elif text == "мой айди":
        if message.from_id != message.peer_id:
            message.reply("Данная команда доступна только в лс бота!")
        else:
            message.reply(message.from_id)
    elif text == "поддержка":
        message.reply("Если у вас возникли какие-то проблемы, обращайтесь к - @deniska_bisekeev")
    elif text == "донат":
        keyboard = VkKeyboard(inline=True)
        keyboard.add_openlink_button("Перейти на сайт", "https://racebotvk.onrender.com")
        t = f"Привет, {message.get_mention(message.from_id)}, чтобы оплатить донат, перейдите на наш сайт."
        message.reply(t, keyboard=keyboard.get_keyboard())
    elif text.startswith("драг"):
        handle_drag_race(message)
    else:
        # Если не распознано - показываем меню
        show_menu(message)

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

@app.route('/health')
def health_check():
    return 'OK', 200

# =============================================================================
# ТЕСТОВЫЙ РОУТ ДЛЯ ПРОВЕРКИ
# =============================================================================

@app.route('/test-bot', methods=['GET'])
def test_bot():
    """Тестовый роут для проверки работы бота"""
    try:
        test_user_id = 819016396
        test_message = "🤖 Бот работает! Сервер отвечает."
        
        vk.messages.send(
            user_id=test_user_id,
            message=test_message,
            random_id=int(time.time() * 1000)
        )
        
        return jsonify({'status': 'success', 'message': 'Тестовое сообщение отправлено'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# =============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    
    print("=" * 60)
    print(f"🌐 Запуск веб-сервера на порту {port}")
    print(f"🤖 ВК бот работает через вебхук")
    print(f"📌 Webhook URL: https://racebotvk.onrender.com/vk-webhook")
    print(f"🔑 Код подтверждения: 9bb1bfa1")
    print(f"🔧 Проверка токена...")
    
    try:
        # Проверяем токен
        vk.users.get(user_ids=1)
        print(f"✅ Токен действителен")
        
        # Проверяем основные функции
        print(f"🔧 Проверка функций...")
        test_functions = ['show_menu', 'show_commands', 'show_races']
        for func_name in test_functions:
            if func_name in globals():
                print(f"✅ Функция {func_name} доступна")
            else:
                print(f"⚠️ Функция {func_name} НЕ найдена")
        
    except Exception as e:
        print(f"❌ Ошибка проверки токена: {e}")
    
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
