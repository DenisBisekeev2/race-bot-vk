#!/usr/bin/env python3
"""
Простое резервное копирование JSON файлов на GitHub
"""
import json
import os
import time
import schedule
import threading
import base64
import requests
from datetime import datetime
from typing import List, Dict
import traceback

class GitHubBackup:
    """
    Простой бэкап файлов на GitHub через API
    """
    
    def __init__(self, github_token: str, repo_name: str, files_to_backup: List[str]):
        """
        Инициализация
        
        Args:
            github_token: GitHub токен
            repo_name: username/repository-name
            files_to_backup: список файлов для бэкапа
        """
        self.token = github_token
        self.repo_name = repo_name
        self.files_to_backup = files_to_backup
        self.is_running = False
        
        # Базовые заголовки
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        print(f"📦 GitHub Backup инициализирован")
        print(f"📂 Репозиторий: {self.repo_name}")
        print(f"📄 Файлов для бэкапа: {len(self.files_to_backup)}")
    
    def check_token(self) -> bool:
        """
        Проверяет токен
        
        Returns:
            bool: рабочий ли токен
        """
        try:
            response = requests.get(
                "https://api.github.com/user",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user = response.json()
                print(f"✅ Токен рабочий. Пользователь: {user.get('login')}")
                return True
            else:
                print(f"❌ Токен не рабочий: {response.status_code}")
                print(f"📄 Ответ: {response.text[:100]}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка проверки токена: {e}")
            return False
    
    def backup_file(self, file_path: str) -> bool:
        """
        Загружает один файл на GitHub
        
        Args:
            file_path: путь к файлу
            
        Returns:
            bool: успешно ли загружено
        """
        if not os.path.exists(file_path):
            print(f"❌ Файл не найден: {file_path}")
            return False
        
        try:
            # Читаем файл
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Кодируем в base64
            content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # Имя файла на GitHub (добавляем дату для истории)
            filename = os.path.basename(file_path)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"backup_{timestamp}_{filename}"
            
            # Создаем данные для GitHub
            data = {
                "message": f"🤖 Бэкап бота: {filename}",
                "content": content_b64
            }
            
            # URL для создания файла
            url = f"https://api.github.com/repos/{self.repo_name}/contents/backups/{backup_filename}"
            
            # Отправляем запрос
            response = requests.put(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code == 201:
                print(f"✅ Файл сохранен: {backup_filename}")
                return True
            else:
                print(f"❌ Ошибка сохранения {filename}: {response.status_code}")
                print(f"📄 Ответ: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка при бэкапе {file_path}: {e}")
            return False
    
    def backup_all_files(self):
        """
        Бэкапит все файлы
        """
        if not self.check_token():
            print("❌ Токен не рабочий, пропускаю бэкап")
            return
        
        print(f"\n🔄 Начинаю бэкап файлов... {datetime.now().strftime('%H:%M:%S')}")
        
        success_count = 0
        
        for file_path in self.files_to_backup:
            if self.backup_file(file_path):
                success_count += 1
            time.sleep(1)  # Пауза между файлами
        
        print(f"📊 Результат: {success_count}/{len(self.files_to_backup)} файлов сохранено")
        
        # Также сохраняем текущие версии файлов
        self.save_current_versions()
    
    def save_current_versions(self):
        """
        Сохраняет текущие версии файлов (перезаписывает)
        """
        print("\n💾 Сохраняю текущие версии файлов...")
        
        for file_path in self.files_to_backup:
            if not os.path.exists(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                filename = os.path.basename(file_path)
                
                # Проверяем существует ли файл
                url = f"https://api.github.com/repos/{self.repo_name}/contents/current/{filename}"
                
                # Сначала пытаемся получить SHA существующего файла
                response = requests.get(url, headers=self.headers)
                
                data = {
                    "message": f"🔄 Обновление: {filename}",
                    "content": content_b64
                }
                
                if response.status_code == 200:
                    # Файл существует, обновляем
                    sha = response.json().get("sha")
                    data["sha"] = sha
                
                # Создаем/обновляем файл
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
                
                if response.status_code in [200, 201]:
                    print(f"✅ Текущая версия сохранена: {filename}")
                else:
                    print(f"⚠️  Не удалось сохранить текущую версию {filename}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Ошибка сохранения текущей версии {file_path}: {e}")
    
    def restore_backup(self, filename: str = None) -> bool:
        """
        Восстанавливает файл из бэкапа
        
        Args:
            filename: имя файла для восстановления (если None - последний)
            
        Returns:
            bool: успешно ли восстановлено
        """
        try:
            # Получаем список бэкапов
            url = f"https://api.github.com/repos/{self.repo_name}/contents/backups"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"❌ Не могу получить список бэкапов: {response.status_code}")
                return False
            
            files = response.json()
            
            if not files:
                print("❌ Нет доступных бэкапов")
                return False
            
            # Ищем нужный файл
            if filename:
                backup_file = None
                for file in files:
                    if file["name"] == filename:
                        backup_file = file
                        break
            else:
                # Берем последний по дате
                files.sort(key=lambda x: x["name"], reverse=True)
                backup_file = files[0]
            
            if not backup_file:
                print(f"❌ Файл {filename} не найден в бэкапах")
                return False
            
            # Скачиваем файл
            download_url = backup_file["download_url"]
            content_response = requests.get(download_url)
            
            if content_response.status_code == 200:
                # Извлекаем оригинальное имя файла
                backup_name = backup_file["name"]
                # Формат: backup_20240101_120000_users.json
                parts = backup_name.split('_')
                if len(parts) >= 4:
                    original_name = '_'.join(parts[3:])  # users.json
                else:
                    original_name = backup_name
                
                # Сохраняем локально
                with open(original_name, 'w', encoding='utf-8') as f:
                    f.write(content_response.text)
                
                print(f"✅ Восстановлен файл: {original_name} из {backup_name}")
                return True
            else:
                print(f"❌ Ошибка скачивания файла: {content_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка восстановления: {e}")
            return False
    
    def start_auto_backup(self, interval_minutes: int = 10):
        """
        Запускает автоматический бэкап
        
        Args:
            interval_minutes: интервал в минутах
        """
        if self.is_running:
            print("⚠️  Автобэкап уже запущен")
            return
        
        # Проверяем токен
        if not self.check_token():
            print("❌ Не могу запустить автобэкап: токен не рабочий")
            return
        
        print(f"⏰ Автоматический бэкап запущен (каждые {interval_minutes} минут)")
        self.is_running = True
        
        # Настраиваем расписание
        schedule.every(interval_minutes).minutes.do(self.backup_all_files)
        
        # Первый бэкап сразу
        print("🔄 Первый бэкап...")
        self.backup_all_files()
        
        # Запускаем планировщик
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
    
    def stop_auto_backup(self):
        """Останавливает автоматический бэкап"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("⏹️  Автобэкап остановлен")
    
    def manual_backup(self):
        """Ручной бэкап"""
        print("🔄 Запуск ручного бэкапа...")
        self.backup_all_files()


# ============================================================================
# Упрощенная версия для быстрого старта
# ============================================================================

class SimpleBackup:
    """
    Упрощенная версия бэкапа
    """
    
    @staticmethod
    def backup_files(token: str, repo: str, files: List[str]):
        """
        Простой бэкап файлов
        
        Args:
            token: GitHub токен
            repo: username/repository
            files: список файлов
        """
        print("🤖 Запускаю бэкап файлов...")
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        for file_path in files:
            if not os.path.exists(file_path):
                print(f"❌ Файл не найден: {file_path}")
                continue
            
            try:
                # Читаем файл
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Кодируем
                import base64
                content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                
                # Создаем уникальное имя
                import datetime
                filename = os.path.basename(file_path)
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"{timestamp}_{filename}"
                
                # Данные для GitHub
                data = {
                    "message": f"Бэкап: {filename}",
                    "content": content_b64
                }
                
                # URL
                url = f"https://api.github.com/repos/{repo}/contents/{backup_name}"
                
                # Отправляем
                import requests
                response = requests.put(url, headers=headers, json=data)
                
                if response.status_code in [200, 201]:
                    print(f"✅ Сохранено: {backup_name}")
                else:
                    print(f"❌ Ошибка {response.status_code}: {response.text[:100]}")
                    
            except Exception as e:
                print(f"❌ Ошибка с файлом {file_path}: {e}")
        
        print("🎉 Бэкап завершен!")


def setup_backup():
    """
    Настройка автоматического бэкапа
    """
    try:
        # Импортируем конфигурацию
        from config import GITHUB_API_KEY
        from github_sync_config import GITHUB_REPO, FILES_TO_SYNC
        
        # Создаем бэкапер
        backup = GitHubBackup(
            github_token=GITHUB_API_KEY,
            repo_name=GITHUB_REPO,
            files_to_backup=FILES_TO_SYNC
        )
        
        # Запускаем авто-бэкап
        backup.start_auto_backup(interval_minutes=10)
        
        return backup
        
    except ImportError:
        print("❌ Не могу импортировать конфигурацию")
        return None
    except Exception as e:
        print(f"❌ Ошибка настройки бэкапа: {e}")
        return None


if __name__ == "__main__":
    # Тест при прямом запуске
    print("🧪 Тест бэкапа")
    
    try:
        from config import GITHUB_API_KEY
        print(f"✅ Токен загружен: {GITHUB_API_KEY[:10]}...")
        
        # Тестовый бэкап
        backup = GitHubBackup(
            github_token=GITHUB_API_KEY,
            repo_name="DenisBisekeev2/race-bot-vk",
            files_to_backup=["test.json"]  # Создай тестовый файл
        )
        
        if backup.check_token():
            print("✅ Токен рабочий")
        else:
            print("❌ Токен не рабочий")
            
    except ImportError:
        print("❌ Создай config.py с GITHUB_API_KEY")
