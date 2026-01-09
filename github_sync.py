#!/usr/bin/env python3
import json
import time
import base64
import schedule
import threading
import os
import requests
from datetime import datetime
from typing import List, Dict, Optional

class GitHubSync:
    """
    Простой класс для синхронизации файлов с GitHub через REST API
    """
    
    def __init__(self, github_token: str, repo_name: str, files_to_sync: List[str], branch: str = "main"):
        """
        Инициализация
        
        Args:
            github_token: GitHub Personal Access Token
            repo_name: username/repository
            files_to_sync: список файлов для синхронизации
            branch: ветка Git
        """
        self.token = github_token
        self.repo_name = repo_name
        self.files_to_sync = files_to_sync
        self.branch = branch
        self.is_running = False
        self.scheduler_thread = None
        
        # Базовые заголовки для всех запросов
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
        # Базовый URL для API
        self.api_base = "https://api.github.com"
        
        print(f"🔗 GitHubSync инициализирован")
        print(f"📂 Репозиторий: {self.repo_name}")
        print(f"📄 Файлов для синхронизации: {len(self.files_to_sync)}")
    
    def _api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """
        Базовый запрос к GitHub API
        
        Args:
            method: GET, POST, PUT, DELETE
            endpoint: часть URL после api.github.com
            data: данные для отправки
            
        Returns:
            Ответ от API в виде словаря
        """
        url = f"{self.api_base}/{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers, timeout=10)
            else:
                raise ValueError(f"Неподдерживаемый метод: {method}")
            
            # Пытаемся разобрать JSON ответ
            try:
                result = response.json()
            except:
                result = {"_raw": response.text}
            
            # Добавляем статус код
            result["_status"] = response.status_code
            result["_ok"] = 200 <= response.status_code < 300
            
            return result
            
        except requests.exceptions.Timeout:
            return {"_error": "Timeout", "_status": 408, "_ok": False}
        except requests.exceptions.ConnectionError:
            return {"_error": "Connection error", "_status": 0, "_ok": False}
        except Exception as e:
            return {"_error": str(e), "_status": 0, "_ok": False}
    
    def check_connection(self) -> bool:
        """
        Проверка подключения к GitHub
        
        Returns:
            bool: успешно ли подключение
        """
        print("🔍 Проверка подключения к GitHub...")
        
        # 1. Проверка пользователя
        user_result = self._api_request("GET", "user")
        if not user_result.get("_ok"):
            print(f"❌ Ошибка проверки пользователя: {user_result.get('_error', user_result)}")
            return False
        
        print(f"✅ Подключен как: {user_result.get('login', 'Unknown')}")
        
        # 2. Проверка репозитория
        repo_result = self._api_request("GET", f"repos/{self.repo_name}")
        if not repo_result.get("_ok"):
            print(f"❌ Ошибка доступа к репозиторию: {repo_result.get('message', 'Unknown error')}")
            print(f"   Проверьте: существует ли репозиторий '{self.repo_name}'?")
            print(f"   Есть ли у вас права на запись?")
            return False
        
        print(f"✅ Репозиторий доступен: {repo_result.get('full_name', self.repo_name)}")
        print(f"📝 Описание: {repo_result.get('description', 'нет')}")
        print(f"🔒 Приватный: {repo_result.get('private', 'unknown')}")
        
        return True
    
    def get_file_sha(self, file_path: str) -> Optional[str]:
        """
        Получить SHA хэш файла на GitHub
        
        Args:
            file_path: путь к файлу в репозитории
            
        Returns:
            SHA хэш файла или None если файл не существует
        """
        result = self._api_request(
            "GET", 
            f"repos/{self.repo_name}/contents/{file_path}?ref={self.branch}"
        )
        
        if result.get("_status") == 404:
            return None  # Файл не существует
        
        if result.get("_ok") and "sha" in result:
            return result["sha"]
        
        return None
    
    def sync_file(self, file_path: str) -> bool:
        """
        Синхронизировать один файл
        
        Args:
            file_path: путь к локальному файлу
            
        Returns:
            bool: успешно ли синхронизировано
        """
        if not os.path.exists(file_path):
            print(f"❌ Локальный файл не найден: {file_path}")
            return False
        
        try:
            # Читаем локальный файл
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Кодируем в base64
            content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # Получаем SHA существующего файла
            sha = self.get_file_sha(file_path)
            
            # Подготавливаем данные для отправки
            data = {
                "message": f"🔄 Автосинхронизация: {file_path} ({datetime.now().strftime('%H:%M:%S')})",
                "content": content_b64,
                "branch": self.branch
            }
            
            if sha:
                # Обновляем существующий файл
                data["sha"] = sha
                endpoint = f"repos/{self.repo_name}/contents/{file_path}"
                method = "PUT"
                action = "обновлен"
            else:
                # Создаем новый файл
                endpoint = f"repos/{self.repo_name}/contents/{file_path}"
                method = "PUT"
                action = "создан"
            
            # Отправляем запрос
            result = self._api_request(method, endpoint, data)
            
            if result.get("_ok"):
                print(f"✅ Файл {file_path} {action} на GitHub")
                return True
            else:
                error_msg = result.get("message", result.get("_error", "Unknown error"))
                print(f"❌ Ошибка синхронизации {file_path}: {error_msg}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при синхронизации {file_path}: {str(e)}")
            return False
    
    def sync_all_files(self):
        """
        Синхронизировать все файлы из списка
        """
        if not self.check_connection():
            print("❌ Не удалось подключиться к GitHub, пропускаю синхронизацию")
            return
        
        print(f"\n🔄 Начинаю синхронизацию... {datetime.now().strftime('%H:%M:%S')}")
        
        results = {"success": 0, "failed": 0}
        
        for file_path in self.files_to_sync:
            if self.sync_file(file_path):
                results["success"] += 1
            else:
                results["failed"] += 1
            
            # Небольшая пауза между файлами
            time.sleep(0.5)
        
        print(f"📊 Результат: {results['success']} успешно, {results['failed']} ошибок")
        
        # Если были ошибки, пробуем через 30 секунд
        if results["failed"] > 0:
            print("🔄 Повторная попытка через 30 секунд...")
            time.sleep(30)
            
            for file_path in self.files_to_sync:
                self.sync_file(file_path)
    
    def start_auto_sync(self, interval_minutes: int = 10):
        """
        Запустить автоматическую синхронизацию
        
        Args:
            interval_minutes: интервал в минутах
        """
        if self.is_running:
            print("⚠️  Автосинхронизация уже запущена")
            return
        
        # Проверяем подключение
        if not self.check_connection():
            print("❌ Не могу запустить автосинхронизацию: нет подключения к GitHub")
            return
        
        print(f"⏰ Автосинхронизация запущена (каждые {interval_minutes} минут)")
        self.is_running = True
        
        # Настраиваем расписание
        schedule.every(interval_minutes).minutes.do(self.sync_all_files)
        
        # Первая синхронизация сразу
        print("🔄 Первая синхронизация...")
        self.sync_all_files()
        
        # Запускаем планировщик в отдельном потоке
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)  # Проверяем каждую секунду
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
    
    def stop_auto_sync(self):
        """
        Остановить автоматическую синхронизацию
        """
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("⏹️  Автосинхронизация остановлена")
    
    def manual_sync(self):
        """
        Ручная синхронизация
        """
        print("🔄 Запуск ручной синхронизации...")
        return self.sync_all_files()


# Простая утилита для быстрой проверки
def test_github_connection():
    """
    Тестирование подключения к GitHub
    """
    print("🧪 Тестирование подключения к GitHub")
    
    # Импортируем конфигурацию
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from config import GITHUB_API_KEY
        from github_sync_config import GITHUB_REPO, FILES_TO_SYNC
        
        print(f"🔑 Токен: {GITHUB_API_KEY[:10]}...")
        print(f"📂 Репозиторий: {GITHUB_REPO}")
        print(f"📄 Файлы: {FILES_TO_SYNC}")
        
        # Создаем синхронизатор
        sync = GitHubSync(
            github_token=GITHUB_API_KEY,
            repo_name=GITHUB_REPO,
            files_to_sync=["test.json"]  # Тестовый файл
        )
        
        # Проверяем подключение
        if sync.check_connection():
            print("\n🎉 Всё работает отлично!")
            return True
        else:
            print("\n❌ Есть проблемы с подключением")
            return False
            
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("Убедитесь, что файлы config.py и github_sync_config.py существуют")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Запуск теста при прямом выполнении файла
    test_github_connection()
