# migrate_to_firebase.py
import json
from firebase_db import firebase_db

print("🚀 Начинаю миграцию данных в Firebase...")

# 1. Пользователи
print("📦 Мигрирую пользователей...")
with open('users.json', 'r', encoding='utf-8') as f:
    users_data = json.load(f)
    for user_id, user_data in users_data.get('users', {}).items():
        firebase_db.save_user(user_id, user_data)
    print(f"✅ Пользователей: {len(users_data.get('users', {}))}")

# 2. Чаты
print("📦 Мигрирую чаты...")
with open('chats.json', 'r', encoding='utf-8') as f:
    chats_data = json.load(f)
    for chat_id, chat_data in chats_data.get('chats', {}).items():
        firebase_db.save_chat(chat_id, chat_data)
    print(f"✅ Чатов: {len(chats_data.get('chats', {}))}")

# 3. Админ данные
print("📦 Мигрирую админ данные...")
with open('admin.json', 'r', encoding='utf-8') as f:
    admin_data = json.load(f)
    firebase_db.save_admin_data(admin_data)
    print("✅ Админ данные мигрированы")

# 4. Кланы
print("📦 Мигрирую кланы...")
with open('klans.json', 'r', encoding='utf-8') as f:
    klans_data = json.load(f)
    for klan_id, klan_data in klans_data.get('klans', {}).items():
        firebase_db.save_klan(klan_id, klan_data)
    print(f"✅ Кланов: {len(klans_data.get('klans', {}))}")

# 5. Машины
print("📦 Мигрирую машины...")
with open('cars.json', 'r', encoding='utf-8') as f:
    cars_data = json.load(f)
    for car_id, car_data in cars_data.get('cars_shop', {}).items():
        firebase_db.set_data(f'cars_shop/{car_id}', car_data)
    print(f"✅ Машин: {len(cars_data.get('cars_shop', {}))}")

# 6. Платежи
print("📦 Мигрирую платежи...")
with open('payments.json', 'r', encoding='utf-8') as f:
    payments_data = json.load(f)
    for payment_id, payment_data in payments_data.get('payments', {}).items():
        firebase_db.save_payment(payment_id, payment_data)
    print(f"✅ Платежей: {len(payments_data.get('payments', {}))}")

print("🎉 Миграция завершена успешно!")
print("🔥 Теперь запускай бота на Render с обновленными переменными окружения!")
