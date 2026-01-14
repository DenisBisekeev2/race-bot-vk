# [file name]: google_sheets_db.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from config import GOOGLE_SHEET_ID

class GoogleSheetsDB:
    def __init__(self):
        self.spreadsheet = None
        self.init_connection()
    
    def init_connection(self):
        """Инициализация подключения к Google Sheets"""
        try:
            # Настройка доступа
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Авторизация
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                'google_credentials.json', scope)
            client = gspread.authorize(creds)
            
            # Открываем таблицу
            self.spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
            print("✅ Подключение к Google Sheets установлено")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к Google Sheets: {e}")
            return False
    
    def get_sheet(self, sheet_name):
        """Получить лист по имени"""
        try:
            if not self.spreadsheet:
                if not self.init_connection():
                    return None
            return self.spreadsheet.worksheet(sheet_name)
        except:
            # Если лист не существует, создаем его
            try:
                return self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            except:
                return None
    
    # ==================== ПОЛЬЗОВАТЕЛИ ====================
    
    def get_user(self, user_id):
        """Получить пользователя по ID"""
        sheet = self.get_sheet("users")
        if not sheet:
            return None
        
        try:
            # Ищем пользователя
            cell = sheet.find(str(user_id))
            if cell:
                row = cell.row
                # Получаем всю строку
                row_data = sheet.row_values(row)
                
                # Заполняем недостающие колонки пустыми значениями
                while len(row_data) < 11:
                    row_data.append("")
                
                user = {
                    'user_id': row_data[0],
                    'username': row_data[1],
                    'money': int(row_data[2]) if row_data[2] else 0,
                    'exp': int(row_data[3]) if row_data[3] else 0,
                    'level': int(row_data[4]) if row_data[4] else 1,
                    'cars': json.loads(row_data[5]) if row_data[5] else {},
                    'active_car': row_data[6] if row_data[6] else None,
                    'referral_code': row_data[7] if row_data[7] else f"ref_{user_id}",
                    'referred_by': row_data[8] if row_data[8] else None,
                    'pistons': int(row_data[9]) if row_data[9] else 0,
                    'car_colors': json.loads(row_data[10]) if row_data[10] else {}
                }
                return user
        except Exception as e:
            print(f"❌ Ошибка чтения пользователя {user_id}: {e}")
        
        return None
    
    def save_user(self, user_id, user_data):
        """Сохранить пользователя"""
        sheet = self.get_sheet("users")
        if not sheet:
            return False
        
        try:
            # Ищем существующую запись
            cell = sheet.find(str(user_id))
            
            # Подготавливаем данные
            row_data = [
                str(user_id),
                user_data.get('username', ''),
                str(user_data.get('money', 0)),
                str(user_data.get('exp', 0)),
                str(user_data.get('level', 1)),
                json.dumps(user_data.get('cars', {}), ensure_ascii=False),
                user_data.get('active_car', ''),
                user_data.get('referral_code', f"ref_{user_id}"),
                user_data.get('referred_by', ''),
                str(user_data.get('pistons', 0)),
                json.dumps(user_data.get('car_colors', {}), ensure_ascii=False)
            ]
            
            if cell:
                # Обновляем существующую строку
                sheet.update(f"A{cell.row}:K{cell.row}", [row_data])
            else:
                # Добавляем новую строку
                sheet.append_row(row_data)
            
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения пользователя {user_id}: {e}")
            return False
    
    def get_all_users(self):
        """Получить всех пользователей"""
        sheet = self.get_sheet("users")
        if not sheet:
            return {}
        
        try:
            users = {}
            data = sheet.get_all_records()
            
            for row in data:
                user_id = row.get('user_id', '')
                if user_id:
                    users[str(user_id)] = {
                        'username': row.get('username', ''),
                        'money': int(row.get('money', 0)),
                        'exp': int(row.get('exp', 0)),
                        'level': int(row.get('level', 1)),
                        'cars': json.loads(row.get('cars', '{}')) if row.get('cars') else {},
                        'active_car': row.get('active_car', ''),
                        'referral_code': row.get('referral_code', f"ref_{user_id}"),
                        'referred_by': row.get('referred_by', ''),
                        'pistons': int(row.get('pistons', 0)),
                        'car_colors': json.loads(row.get('car_colors', '{}')) if row.get('car_colors') else {}
                    }
            
            return users
        except Exception as e:
            print(f"❌ Ошибка чтения всех пользователей: {e}")
            return {}
    
    # ==================== ЧАТЫ ====================
    
    def get_chat(self, chat_id):
        """Получить чат по ID"""
        sheet = self.get_sheet("chats")
        if not sheet:
            return None
        
        try:
            cell = sheet.find(str(chat_id))
            if cell:
                row = cell.row
                row_data = sheet.row_values(row)
                
                while len(row_data) < 5:
                    row_data.append("")
                
                return {
                    'chat_id': row_data[0],
                    'title': row_data[1],
                    'premium': row_data[2].lower() == 'true',
                    'registered_date': row_data[3],
                    'total_races': int(row_data[4]) if row_data[4] else 0
                }
        except:
            pass
        
        return None
    
    def save_chat(self, chat_id, chat_data):
        """Сохранить чат"""
        sheet = self.get_sheet("chats")
        if not sheet:
            return False
        
        try:
            cell = sheet.find(str(chat_id))
            
            row_data = [
                str(chat_id),
                chat_data.get('title', ''),
                'TRUE' if chat_data.get('premium', False) else 'FALSE',
                chat_data.get('registered_date', ''),
                str(chat_data.get('total_races', 0))
            ]
            
            if cell:
                sheet.update(f"A{cell.row}:E{cell.row}", [row_data])
            else:
                sheet.append_row(row_data)
            
            return True
        except:
            return False
    
    def get_all_chats(self):
        """Получить все чаты"""
        sheet = self.get_sheet("chats")
        if not sheet:
            return {}
        
        try:
            chats = {}
            data = sheet.get_all_records()
            
            for row in data:
                chat_id = row.get('chat_id', '')
                if chat_id:
                    chats[str(chat_id)] = {
                        'title': row.get('title', ''),
                        'premium': row.get('premium', '').lower() == 'true',
                        'registered_date': row.get('registered_date', ''),
                        'total_races': int(row.get('total_races', 0))
                    }
            
            return chats
        except:
            return {}
    
    # ==================== МАШИНЫ ====================
    
    def get_car_shop(self):
        """Получить магазин машин"""
        sheet = self.get_sheet("cars_shop")
        if not sheet:
            return {}
        
        try:
            cars = {}
            data = sheet.get_all_records()
            
            for row in data:
                car_id = row.get('car_id', '')
                if car_id:
                    cars[str(car_id)] = {
                        'name': row.get('name', ''),
                        'price': int(row.get('price', 0)),
                        'hp': int(row.get('hp', 0)),
                        'max_speed': int(row.get('max_speed', 0)),
                        'tire_health': int(row.get('tire_health', 100)),
                        'durability': int(row.get('durability', 100))
                    }
            
            return cars
        except:
            return {}
    
    # ==================== АДМИН ДАННЫЕ ====================
    
    def get_admin_data(self):
        """Получить админ данные"""
        admin_data = {
            'ban': {'users_ids': []},
            'freeze': {'users_ids': []},
            'pred': {},
            'moders': {'users_ids': []}
        }
        
        try:
            # Модераторы
            moders_sheet = self.get_sheet("admin_moders")
            if moders_sheet:
                data = moders_sheet.get_all_records()
                for row in data:
                    user_id = str(row.get('user_id', ''))
                    if user_id:
                        admin_data['moders']['users_ids'].append(user_id)
                        admin_data['moders'][user_id] = {
                            'status': row.get('status', ''),
                            'reports': int(row.get('reports', 0)),
                            'perm': json.loads(row.get('perm', '["basic"]'))
                        }
            
            # Баны
            ban_sheet = self.get_sheet("admin_ban")
            if ban_sheet:
                data = ban_sheet.get_all_records()
                for row in data:
                    user_id = str(row.get('user_id', ''))
                    if user_id:
                        admin_data['ban']['users_ids'].append(user_id)
                        admin_data['ban'][user_id] = {
                            'days': int(row.get('days', 0)),
                            'time': int(row.get('time', 0)),
                            'reason': row.get('reason', '')
                        }
        except Exception as e:
            print(f"❌ Ошибка чтения админ данных: {e}")
        
        return admin_data
    
    def save_admin_data(self, admin_data):
        """Сохранить админ данные"""
        try:
            # Сохраняем модераторов
            moders_sheet = self.get_sheet("admin_moders")
            if moders_sheet:
                moders_sheet.clear()
                moders_sheet.append_row(['user_id', 'status', 'reports', 'perm'])
                
                for user_id in admin_data.get('moders', {}).get('users_ids', []):
                    if user_id in admin_data['moders']:
                        moders_sheet.append_row([
                            user_id,
                            admin_data['moders'][user_id].get('status', ''),
                            str(admin_data['moders'][user_id].get('reports', 0)),
                            json.dumps(admin_data['moders'][user_id].get('perm', []))
                        ])
            
            # Сохраняем баны
            ban_sheet = self.get_sheet("admin_ban")
            if ban_sheet:
                ban_sheet.clear()
                ban_sheet.append_row(['user_id', 'days', 'time', 'reason'])
                
                for user_id in admin_data.get('ban', {}).get('users_ids', []):
                    if user_id in admin_data['ban']:
                        ban_sheet.append_row([
                            user_id,
                            str(admin_data['ban'][user_id].get('days', 0)),
                            str(admin_data['ban'][user_id].get('time', 0)),
                            admin_data['ban'][user_id].get('reason', '')
                        ])
            
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения админ данных: {e}")
            return False

# Создаем глобальный экземпляр
gs_db = GoogleSheetsDB()

# ==================== ФУНКЦИИ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ ====================

def load_data(filename):
    """Замена старой функции load_data"""
    if filename == 'users.json':
        users = gs_db.get_all_users()
        return {'users': users}
    
    elif filename == 'chats.json':
        chats = gs_db.get_all_chats()
        return {'chats': chats}
    
    elif filename == 'cars.json':
        cars = gs_db.get_car_shop()
        return {'cars_shop': cars}
    
    elif filename == 'admin.json':
        return gs_db.get_admin_data()
    
    elif filename == 'klans.json':
        # Пока возвращаем пустую структуру
        return {'klans': {}, 'klan_battles': {}, 'next_klan_id': 1}
    
    elif filename == 'payments.json':
        return {'payments': {}, 'last_check': 0}
    
    elif filename == 'global_races.json':
        return {'waiting_players': {}, 'active_races': {}}
    
    return {}

def save_data(data, filename):
    """Замена старой функции save_data"""
    if filename == 'users.json':
        for user_id, user_data in data.get('users', {}).items():
            gs_db.save_user(user_id, user_data)
        return True
    
    elif filename == 'chats.json':
        for chat_id, chat_data in data.get('chats', {}).items():
            gs_db.save_chat(chat_id, chat_data)
        return True
    
    elif filename == 'admin.json':
        return gs_db.save_admin_data(data)
    
    # Остальные файлы пока не реализованы
    return True
