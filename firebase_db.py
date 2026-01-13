# [file name]: firebase_db.py
import firebase_admin
from firebase_admin import credentials, db
from firebase_admin.exceptions import FirebaseError
import json
import time
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
                    cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT)
                    firebase_admin.initialize_app(cred, {
                        'databaseURL': 'https://racebotvk-default-rtdb.europe-west1.firebasedatabase.app/'
                    })
                    logger.info("✅ Firebase инициализирован")
                else:
                    logger.error("❌ FIREBASE_SERVICE_ACCOUNT не настроен")
                    return False
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Firebase: {e}")
            return False
    
    # ==================== ОСНОВНЫЕ МЕТОДЫ ====================
    
    def get_ref(self, path):
        """Получить ссылку на путь в базе"""
        try:
            return db.reference(path)
        except Exception as e:
            logger.error(f"❌ Ошибка получения ссылки {path}: {e}")
            return None
    
    def get_data(self, path):
        """Получить данные по пути"""
        try:
            ref = self.get_ref(path)
            if ref:
                data = ref.get()
                return data if data is not None else {}
        except Exception as e:
            logger.error(f"❌ Ошибка получения данных из {path}: {e}")
        return {}
    
    def set_data(self, path, data):
        """Установить данные по пути"""
        try:
            ref = self.get_ref(path)
            if ref:
                ref.set(data)
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка записи данных в {path}: {e}")
        return False
    
    def update_data(self, path, updates):
        """Обновить данные по пути"""
        try:
            ref = self.get_ref(path)
            if ref:
                ref.update(updates)
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка обновления данных в {path}: {e}")
        return False
    
    def delete_data(self, path):
        """Удалить данные по пути"""
        try:
            ref = self.get_ref(path)
            if ref:
                ref.delete()
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка удаления данных из {path}: {e}")
        return False
    
    def push_data(self, path, data):
        """Добавить данные с авто-generated ID"""
        try:
            ref = self.get_ref(path)
            if ref:
                new_ref = ref.push(data)
                return new_ref.key
        except Exception as e:
            logger.error(f"❌ Ошибка добавления данных в {path}: {e}")
        return None
    
    # ==================== МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ====================
    
    def get_user(self, user_id):
        """Получить данные пользователя"""
        return self.get_data(f'users/{user_id}')
    
    def save_user(self, user_id, user_data):
        """Сохранить данные пользователя"""
        return self.set_data(f'users/{user_id}', user_data)
    
    def update_user(self, user_id, updates):
        """Обновить данные пользователя"""
        return self.update_data(f'users/{user_id}', updates)
    
    def delete_user(self, user_id):
        """Удалить пользователя"""
        return self.delete_data(f'users/{user_id}')
    
    def get_all_users(self):
        """Получить всех пользователей"""
        return self.get_data('users') or {}
    
    def user_exists(self, user_id):
        """Проверить существование пользователя"""
        return bool(self.get_user(user_id))
    
    # ==================== МЕТОДЫ ДЛЯ ЧАТОВ ====================
    
    def get_chat(self, chat_id):
        """Получить данные чата"""
        return self.get_data(f'chats/{chat_id}')
    
    def save_chat(self, chat_id, chat_data):
        """Сохранить данные чата"""
        return self.set_data(f'chats/{chat_id}', chat_data)
    
    def update_chat(self, chat_id, updates):
        """Обновить данные чата"""
        return self.update_data(f'chats/{chat_id}', updates)
    
    def get_all_chats(self):
        """Получить все чаты"""
        return self.get_data('chats') or {}
    
    def chat_exists(self, chat_id):
        """Проверить существование чата"""
        return bool(self.get_chat(chat_id))
    
    # ==================== МЕТОДЫ ДЛЯ МАШИН ====================
    
    def get_car_shop(self):
        """Получить все машины в магазине"""
        return self.get_data('cars_shop') or {}
    
    def get_car(self, car_id):
        """Получить машину по ID"""
        return self.get_data(f'cars_shop/{car_id}')
    
    def save_car(self, car_id, car_data):
        """Сохранить машину"""
        return self.set_data(f'cars_shop/{car_id}', car_data)
    
    # ==================== МЕТОДЫ ДЛЯ АДМИН ДАННЫХ ====================
    
    def get_admin_data(self):
        """Получить админ данные"""
        return self.get_data('admin') or {}
    
    def save_admin_data(self, admin_data):
        """Сохранить админ данные"""
        return self.set_data('admin', admin_data)
    
    def update_admin(self, updates):
        """Обновить админ данные"""
        return self.update_data('admin', updates)
    
    # --- Бан система ---
    def ban_user(self, user_id, days, reason):
        """Забанить пользователя"""
        try:
            user_id_str = str(user_id)
            ban_data = {
                'days': days,
                'time': int(time.time()),
                'reason': reason
            }
            
            # Получаем текущие данные
            admin_data = self.get_admin_data()
            
            # Инициализируем структуру если нет
            if 'ban' not in admin_data:
                admin_data['ban'] = {'users_ids': []}
            
            # Добавляем пользователя
            admin_data['ban'][user_id_str] = ban_data
            if user_id_str not in admin_data['ban']['users_ids']:
                admin_data['ban']['users_ids'].append(user_id_str)
            
            # Сохраняем
            return self.save_admin_data(admin_data)
        except Exception as e:
            logger.error(f"❌ Ошибка бана пользователя {user_id}: {e}")
            return False
    
    def unban_user(self, user_id):
        """Разбанить пользователя"""
        try:
            user_id_str = str(user_id)
            admin_data = self.get_admin_data()
            
            if 'ban' not in admin_data:
                return True
            
            # Удаляем из бана
            if user_id_str in admin_data['ban']:
                del admin_data['ban'][user_id_str]
            
            # Удаляем из списка
            if 'users_ids' in admin_data['ban'] and user_id_str in admin_data['ban']['users_ids']:
                admin_data['ban']['users_ids'].remove(user_id_str)
            
            # Сохраняем
            return self.save_admin_data(admin_data)
        except Exception as e:
            logger.error(f"❌ Ошибка разбана пользователя {user_id}: {e}")
            return False
    
    def is_user_banned(self, user_id):
        """Проверить, забанен ли пользователь"""
        try:
            user_id_str = str(user_id)
            admin_data = self.get_admin_data()
            
            if 'ban' not in admin_data:
                return False
            
            # Проверяем в списке забаненных
            if 'users_ids' in admin_data['ban']:
                return user_id_str in admin_data['ban']['users_ids']
            
            # Проверяем в объекте банов
            return user_id_str in admin_data['ban']
        except:
            return False
    
    def get_ban_info(self, user_id):
        """Получить информацию о бане"""
        user_id_str = str(user_id)
        return self.get_data(f'admin/ban/{user_id_str}')
    
    # --- Модераторы ---
    def add_moderator(self, user_id, status, perm):
        """Добавить модератора"""
        try:
            user_id_str = str(user_id)
            admin_data = self.get_admin_data()
            
            # Инициализируем структуру если нет
            if 'moders' not in admin_data:
                admin_data['moders'] = {'users_ids': []}
            
            # Добавляем модератора
            admin_data['moders'][user_id_str] = {
                'status': status,
                'reports': 0,
                'perm': [perm]
            }
            
            # Добавляем в список
            if user_id_str not in admin_data['moders']['users_ids']:
                admin_data['moders']['users_ids'].append(user_id_str)
            
            # Сохраняем
            return self.save_admin_data(admin_data)
        except Exception as e:
            logger.error(f"❌ Ошибка добавления модератора {user_id}: {e}")
            return False
    
    def remove_moderator(self, user_id):
        """Удалить модератора"""
        try:
            user_id_str = str(user_id)
            admin_data = self.get_admin_data()
            
            if 'moders' not in admin_data:
                return True
            
            # Удаляем модератора
            if user_id_str in admin_data['moders']:
                del admin_data['moders'][user_id_str]
            
            # Удаляем из списка
            if 'users_ids' in admin_data['moders'] and user_id_str in admin_data['moders']['users_ids']:
                admin_data['moders']['users_ids'].remove(user_id_str)
            
            # Сохраняем
            return self.save_admin_data(admin_data)
        except Exception as e:
            logger.error(f"❌ Ошибка удаления модератора {user_id}: {e}")
            return False
    
    def is_moderator(self, user_id):
        """Проверить, является ли модератором"""
        try:
            user_id_str = str(user_id)
            admin_data = self.get_admin_data()
            
            if 'moders' not in admin_data:
                return False
            
            # Проверяем в списке модераторов
            if 'users_ids' in admin_data['moders']:
                return user_id_str in admin_data['moders']['users_ids']
            
            # Проверяем в объекте модераторов
            return user_id_str in admin_data['moders']
        except:
            return False
    
    def get_moderator_info(self, user_id):
        """Получить информацию о модераторе"""
        user_id_str = str(user_id)
        return self.get_data(f'admin/moders/{user_id_str}')
    
    # ==================== МЕТОДЫ ДЛЯ КЛАНОВ ====================
    
    def get_klan(self, klan_id):
        """Получить данные клана"""
        return self.get_data(f'klans/{klan_id}')
    
    def save_klan(self, klan_id, klan_data):
        """Сохранить данные клана"""
        return self.set_data(f'klans/{klan_id}', klan_data)
    
    def update_klan(self, klan_id, updates):
        """Обновить данные клана"""
        return self.update_data(f'klans/{klan_id}', updates)
    
    def delete_klan(self, klan_id):
        """Удалить клан"""
        return self.delete_data(f'klans/{klan_id}')
    
    def get_all_klans(self):
        """Получить все кланы"""
        return self.get_data('klans') or {}
    
    def get_next_klan_id(self):
        """Получить следующий ID для клана"""
        counter = self.get_data('counters/klans') or 0
        next_id = counter + 1
        self.set_data('counters/klans', next_id)
        return next_id
    
    # ==================== МЕТОДЫ ДЛЯ ПЛАТЕЖЕЙ ====================
    
    def get_payment(self, payment_id):
        """Получить данные платежа"""
        return self.get_data(f'payments/{payment_id}')
    
    def save_payment(self, payment_id, payment_data):
        """Сохранить данные платежа"""
        return self.set_data(f'payments/{payment_id}', payment_data)
    
    def update_payment(self, payment_id, updates):
        """Обновить данные платежа"""
        return self.update_data(f'payments/{payment_id}', updates)
    
    def get_all_payments(self):
        """Получить все платежи"""
        return self.get_data('payments') or {}
    
    # ==================== МЕТОДЫ ДЛЯ ГОНОК ====================
    
    def save_race(self, race_id, race_data):
        """Сохранить данные гонки"""
        return self.set_data(f'races/{race_id}', race_data)
    
    def get_race(self, race_id):
        """Получить данные гонки"""
        return self.get_data(f'races/{race_id}')
    
    def delete_race(self, race_id):
        """Удалить гонку"""
        return self.delete_data(f'races/{race_id}')
    
    # ==================== УТИЛИТНЫЕ МЕТОДЫ ====================
    
    def increment_counter(self, path):
        """Увеличить счетчик"""
        try:
            current = self.get_data(path) or 0
            new_value = current + 1
            self.set_data(path, new_value)
            return new_value
        except:
            return 1
    
    def migrate_json_to_firebase(self, json_file_path, firebase_path):
        """Миграция данных из JSON файла в Firebase"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Если это словарь с вложенной структурой
            if isinstance(json_data, dict):
                for key, value in json_data.items():
                    self.set_data(f'{firebase_path}/{key}', value)
            else:
                self.set_data(firebase_path, json_data)
            
            logger.info(f"✅ Мигрировано из {json_file_path} в {firebase_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка миграции {json_file_path}: {e}")
            return False

# Создаем глобальный экземпляр
firebase_db = FirebaseDB()

# ==================== ФУНКЦИИ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ ====================

def load_data(filename):
    """Замена старой функции load_data для обратной совместимости"""
    if not firebase_db.init_firebase():
        return _get_empty_structure(filename)
    
    try:
        if filename == 'users.json':
            users = firebase_db.get_all_users()
            return {'users': users}
        
        elif filename == 'chats.json':
            chats = firebase_db.get_all_chats()
            return {'chats': chats}
        
        elif filename == 'cars.json':
            cars = firebase_db.get_car_shop()
            return {'cars_shop': cars}
        
        elif filename == 'admin.json':
            return firebase_db.get_admin_data()
        
        elif filename == 'klans.json':
            klans = firebase_db.get_all_klans()
            # Сохраняем структуру как в старом JSON
            result = {'klans': klans}
            
            # Находим максимальный ID для next_klan_id
            max_id = 0
            if klans:
                for klan_id in klans.keys():
                    try:
                        klan_id_int = int(klan_id)
                        if klan_id_int > max_id:
                            max_id = klan_id_int
                    except:
                        pass
            result['next_klan_id'] = max_id + 1
            
            return result
        
        elif filename == 'payments.json':
            payments = firebase_db.get_all_payments()
            return {'payments': payments, 'last_check': 0}
        
        elif filename == 'global_races.json':
            return {'waiting_players': {}, 'active_races': {}}
        
        else:
            return _get_empty_structure(filename)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в load_data для {filename}: {e}")
        return _get_empty_structure(filename)

def save_data(data, filename):
    """Замена старой функции save_data для обратной совместимости"""
    if not firebase_db.init_firebase():
        return False
    
    try:
        if filename == 'users.json':
            users = data.get('users', {})
            for user_id, user_data in users.items():
                firebase_db.save_user(user_id, user_data)
            return True
        
        elif filename == 'chats.json':
            chats = data.get('chats', {})
            for chat_id, chat_data in chats.items():
                firebase_db.save_chat(chat_id, chat_data)
            return True
        
        elif filename == 'admin.json':
            return firebase_db.save_admin_data(data)
        
        elif filename == 'klans.json':
            klans = data.get('klans', {})
            for klan_id, klan_data in klans.items():
                firebase_db.save_klan(klan_id, klan_data)
            return True
        
        elif filename == 'payments.json':
            payments = data.get('payments', {})
            for payment_id, payment_data in payments.items():
                firebase_db.save_payment(payment_id, payment_data)
            return True
        
        else:
            logger.warning(f"⚠️ save_data: неизвестный файл {filename}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка в save_data для {filename}: {e}")
        return False

def _get_empty_structure(filename):
    """Получить пустую структуру для файла"""
    if filename == 'users.json':
        return {'users': {}}
    elif filename == 'chats.json':
        return {'chats': {}}
    elif filename == 'cars.json':
        return {'cars_shop': {}}
    elif filename == 'admin.json':
        return {'ban': {'users_ids': []}, 'freeze': {'users_ids': []}, 'pred': {}, 'moders': {'users_ids': []}}
    elif filename == 'klans.json':
        return {'klans': {}, 'klan_battles': {}, 'next_klan_id': 1}
    elif filename == 'payments.json':
        return {'payments': {}, 'last_check': 0}
    elif filename == 'global_races.json':
        return {'waiting_players': {}, 'active_races': {}}
    return {}
