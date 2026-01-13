# [file name]: firebase_db.py
import firebase_admin
from firebase_admin import credentials, db
from firebase_admin.exceptions import FirebaseError
import json
import logging
from config import FIREBASE_SERVICE_ACCOUNT

logger = logging.getLogger(__name__)

class FirebaseDB:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseDB, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.init_firebase()
            self._initialized = True
    
    def init_firebase(self):
        """Инициализация Firebase"""
        try:
            if not firebase_admin._apps:
                if FIREBASE_SERVICE_ACCOUNT:
                    # Используем service account для продакшена
                    cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT)
                    firebase_admin.initialize_app(cred, {
                        'databaseURL': 'https://racebotvk-default-rtdb.europe-west1.firebasedatabase.app/'
                    })
                else:
                    # Для разработки (тестовый режим)
                    firebase_admin.initialize_app(options={
                        'databaseURL': 'https://racebotvk-default-rtdb.europe-west1.firebasedatabase.app/'
                    })
                
                logger.info("✅ Firebase инициализирован")
            else:
                logger.info("✅ Firebase уже инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Firebase: {e}")
            raise
    
    # ==================== БАЗОВЫЕ МЕТОДЫ ====================
    
    def get_ref(self, path):
        """Получить ссылку на путь в базе"""
        return db.reference(path)
    
    def get_data(self, path):
        """Получить данные по пути"""
        try:
            ref = self.get_ref(path)
            data = ref.get()
            return data if data is not None else {}
        except Exception as e:
            logger.error(f"❌ Ошибка получения данных из {path}: {e}")
            return {}
    
    def set_data(self, path, data):
        """Установить данные по пути"""
        try:
            ref = self.get_ref(path)
            ref.set(data)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка записи данных в {path}: {e}")
            return False
    
    def update_data(self, path, updates):
        """Обновить данные по пути"""
        try:
            ref = self.get_ref(path)
            ref.update(updates)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка обновления данных в {path}: {e}")
            return False
    
    def delete_data(self, path):
        """Удалить данные по пути"""
        try:
            ref = self.get_ref(path)
            ref.delete()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка удаления данных из {path}: {e}")
            return False
    
    def push_data(self, path, data):
        """Добавить данные с авто-generated ID"""
        try:
            ref = self.get_ref(path)
            new_ref = ref.push(data)
            return new_ref.key
        except Exception as e:
            logger.error(f"❌ Ошибка добавления данных в {path}: {e}")
            return None
    
    # ==================== СПЕЦИФИЧНЫЕ МЕТОДЫ ДЛЯ БОТА ====================
    
    # --- ПОЛЬЗОВАТЕЛИ ---
    def get_user(self, user_id):
        """Получить данные пользователя"""
        return self.get_data(f'users/{user_id}')
    
    def save_user(self, user_id, user_data):
        """Сохранить данные пользователя"""
        return self.update_data(f'users/{user_id}', user_data)
    
    def delete_user(self, user_id):
        """Удалить пользователя"""
        return self.delete_data(f'users/{user_id}')
    
    def get_all_users(self):
        """Получить всех пользователей"""
        return self.get_data('users')
    
    def update_user_field(self, user_id, field, value):
        """Обновить поле пользователя"""
        return self.update_data(f'users/{user_id}', {field: value})
    
    # --- ЧАТЫ ---
    def get_chat(self, chat_id):
        """Получить данные чата"""
        return self.get_data(f'chats/{chat_id}')
    
    def save_chat(self, chat_id, chat_data):
        """Сохранить данные чата"""
        return self.update_data(f'chats/{chat_id}', chat_data)
    
    def get_all_chats(self):
        """Получить все чаты"""
        return self.get_data('chats')
    
    # --- МАШИНЫ (магазин) ---
    def get_car_shop(self):
        """Получить все машины в магазине"""
        return self.get_data('cars_shop')
    
    def get_car(self, car_id):
        """Получить машину по ID"""
        return self.get_data(f'cars_shop/{car_id}')
    
    # --- АДМИН ДАННЫЕ ---
    def get_admin_data(self):
        """Получить админ данные"""
        return self.get_data('admin')
    
    def save_admin_data(self, admin_data):
        """Сохранить админ данные"""
        return self.set_data('admin', admin_data)
    
    def update_admin_field(self, path, value):
        """Обновить поле в админ данных"""
        return self.update_data(f'admin/{path}', value)
    
    # Бан система
    def ban_user(self, user_id, days, reason):
        """Забанить пользователя"""
        ban_data = {
            'days': days,
            'time': int(time.time()),
            'reason': reason
        }
        
        # Обновляем несколько полей
        updates = {
            f'ban/{user_id}': ban_data,
            'ban/users_ids': {user_id: True}
        }
        
        return self.update_data('admin', updates)
    
    def unban_user(self, user_id):
        """Разбанить пользователя"""
        updates = {
            f'ban/{user_id}': None,
            f'ban/users_ids/{user_id}': None
        }
        return self.update_data('admin', updates)
    
    def is_user_banned(self, user_id):
        """Проверить, забанен ли пользователь"""
        ban_data = self.get_data(f'admin/ban/{user_id}')
        return ban_data is not None
    
    # Модераторы
    def add_moderator(self, user_id, status, perm):
        """Добавить модератора"""
        moderator_data = {
            'status': status,
            'reports': 0,
            'perm': [perm]
        }
        
        updates = {
            f'moders/{user_id}': moderator_data,
            f'moders/users_ids/{user_id}': True
        }
        
        return self.update_data('admin', updates)
    
    def remove_moderator(self, user_id):
        """Удалить модератора"""
        updates = {
            f'moders/{user_id}': None,
            f'moders/users_ids/{user_id}': None
        }
        return self.update_data('admin', updates)
    
    def is_moderator(self, user_id):
        """Проверить, является ли модератором"""
        return self.get_data(f'admin/moders/{user_id}') is not None
    
    # --- КЛАНЫ ---
    def get_klan(self, klan_id):
        """Получить данные клана"""
        return self.get_data(f'klans/{klan_id}')
    
    def save_klan(self, klan_id, klan_data):
        """Сохранить данные клана"""
        return self.update_data(f'klans/{klan_id}', klan_data)
    
    def get_all_klans(self):
        """Получить все кланы"""
        return self.get_data('klans')
    
    def create_klan(self, klan_id, klan_data):
        """Создать новый клан"""
        return self.set_data(f'klans/{klan_id}', klan_data)
    
    def delete_klan(self, klan_id):
        """Удалить клан"""
        return self.delete_data(f'klans/{klan_id}')
    
    # --- ГОНКИ ---
    def get_race(self, race_id):
        """Получить данные гонки"""
        return self.get_data(f'races/{race_id}')
    
    def save_race(self, race_id, race_data):
        """Сохранить данные гонки"""
        return self.set_data(f'races/{race_id}', race_data)
    
    def delete_race(self, race_id):
        """Удалить гонку"""
        return self.delete_data(f'races/{race_id}')
    
    # --- ПЛАТЕЖИ ---
    def get_payment(self, payment_id):
        """Получить данные платежа"""
        return self.get_data(f'payments/{payment_id}')
    
    def save_payment(self, payment_id, payment_data):
        """Сохранить данные платежа"""
        return self.set_data(f'payments/{payment_id}', payment_data)
    
    def update_payment(self, payment_id, updates):
        """Обновить данные платежа"""
        return self.update_data(f'payments/{payment_id}', updates)
    
    # ==================== УТИЛИТЫ ====================
    
    def get_next_id(self, path):
        """Получить следующий ID для автоинкремента"""
        try:
            counter_ref = self.get_ref(f'counters/{path}')
            current_id = counter_ref.get() or 0
            next_id = current_id + 1
            counter_ref.set(next_id)
            return next_id
        except Exception as e:
            logger.error(f"❌ Ошибка получения следующего ID для {path}: {e}")
            return 1
    
    def migrate_from_json(self, json_data, base_path):
        """Миграция данных из JSON в Firebase"""
        try:
            for key, value in json_data.items():
                self.set_data(f'{base_path}/{key}', value)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка миграции в {base_path}: {e}")
            return False

# Создаем глобальный экземпляр
firebase_db = FirebaseDB()

# Функции для обратной совместимости со старым кодом
def load_data(filename):
    """Замена старой функции load_data для обратной совместимости"""
    mapping = {
        'users.json': lambda: firebase_db.get_all_users(),
        'chats.json': lambda: {'chats': firebase_db.get_all_chats()},
        'cars.json': lambda: {'cars_shop': firebase_db.get_car_shop()},
        'admin.json': lambda: firebase_db.get_admin_data(),
        'klans.json': lambda: {'klans': firebase_db.get_all_klans()},
        'global_races.json': lambda: {'waiting_players': {}, 'active_races': {}},
        'payments.json': lambda: {'payments': {}, 'last_check': 0}
    }
    
    if filename in mapping:
        return mapping[filename]()
    return {}

def save_data(data, filename):
    """Замена старой функции save_data для обратной совместимости"""
    if filename == 'users.json':
        for user_id, user_data in data.get('users', {}).items():
            firebase_db.save_user(user_id, user_data)
    elif filename == 'chats.json':
        for chat_id, chat_data in data.get('chats', {}).items():
            firebase_db.save_chat(chat_id, chat_data)
    elif filename == 'admin.json':
        firebase_db.save_admin_data(data)
    elif filename == 'klans.json':
        for klan_id, klan_data in data.get('klans', {}).items():
            firebase_db.save_klan(klan_id, klan_data)
    return True
