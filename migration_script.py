# migration_script.py
import json
from firebase_db import firebase_db

def migrate_all_data():
    # Мигрируем users.json
    with open('users.json', 'r', encoding='utf-8') as f:
        users_data = json.load(f)
        for user_id, user_data in users_data.get('users', {}).items():
            firebase_db.save_user(user_id, user_data)
    
    # Мигрируем chats.json
    with open('chats.json', 'r', encoding='utf-8') as f:
        chats_data = json.load(f)
        for chat_id, chat_data in chats_data.get('chats', {}).items():
            firebase_db.save_chat(chat_id, chat_data)
    
    # Мигрируем admin.json
    with open('admin.json', 'r', encoding='utf-8') as f:
        admin_data = json.load(f)
        firebase_db.save_admin_data(admin_data)
    
    # Мигрируем klans.json
    with open('klans.json', 'r', encoding='utf-8') as f:
        klans_data = json.load(f)
        for klan_id, klan_data in klans_data.get('klans', {}).items():
            firebase_db.save_klan(klan_id, klan_data)
    
    # Мигрируем cars.json
    with open('cars.json', 'r', encoding='utf-8') as f:
        cars_data = json.load(f)
        for car_id, car_data in cars_data.get('cars_shop', {}).items():
            firebase_db.update_data(f'cars_shop/{car_id}', car_data)
    
    print("✅ Миграция завершена!")

if __name__ == "__main__":
    migrate_all_data()
