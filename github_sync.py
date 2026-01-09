import json
import time
import schedule
import threading
from github import Github, GithubException
import os
from datetime import datetime
import traceback

class GitHubSync:
    """
    Класс для автоматической синхронизации JSON файлов с GitHub
    """
    
    def __init__(self, github_token, repo_name, files_to_sync, branch="main"):
        """
        Инициализация синхронизатора
        
        Args:
            github_token: GitHub API токен
            repo_name: Название репозитория (username/repo)
            files_to_sync: Список файлов для синхронизации
            branch: Ветка GitHub
        """
        self.github_token = github_token
        self.repo_name = repo_name
        self.files_to_sync = files_to_sync
        self.branch = branch
        self.is_running = False
        self.scheduler_thread = None
        
        # Инициализируем GitHub клиент
        try:
            self.g = Github(github_token)
            self.repo = self.g.get_repo(repo_name)
            print(f"✅ GitHubSync подключен к репозиторию: {repo_name}")
        except Exception as e:
            print(f"❌ Ошибка подключения к GitHub: {e}")
            self.repo = None
    
    def sync_file(self, file_path):
        """
        Синхронизирует один файл с GitHub
        
        Args:
            file_path: Путь к локальному файлу
        Returns:
            bool: Успешно ли обновление
        """
        if not self.repo:
            print(f"❌ GitHub не подключен, пропускаю {file_path}")
            return False
        
        try:
            # Читаем локальный файл
            if not os.path.exists(file_path):
                print(f"❌ Локальный файл не найден: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                local_content = f.read()
            
            # Проверяем, изменился ли файл
            try:
                # Получаем информацию о файле на GitHub
                github_file = self.repo.get_contents(file_path, ref=self.branch)
                
                # Если контент одинаковый, пропускаем
                if github_file.decoded_content.decode('utf-8') == local_content:
                    print(f"⏭️  Файл {file_path} не изменился, пропускаю")
                    return True
                
                # Обновляем файл
                self.repo.update_file(
                    path=file_path,
                    message=f"🔄 Автосинхронизация: {file_path} ({datetime.now().strftime('%H:%M:%S')})",
                    content=local_content,
                    sha=github_file.sha,
                    branch=self.branch
                )
                print(f"✅ Обновлен: {file_path}")
                
            except GithubException as e:
                # Если файл не существует на GitHub, создаем его
                if e.status == 404:
                    self.repo.create_file(
                        path=file_path,
                        message=f"📄 Создан: {file_path} ({datetime.now().strftime('%H:%M:%S')})",
                        content=local_content,
                        branch=self.branch
                    )
                    print(f"📄 Создан новый файл: {file_path}")
                else:
                    raise e
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка синхронизации {file_path}: {str(e)}")
            return False
    
    def sync_all_files(self):
        """
        Синхронизирует все файлы из списка
        """
        if not self.repo:
            return
        
        print(f"\n🔄 Начинаю синхронизацию с GitHub... {datetime.now().strftime('%H:%M:%S')}")
        
        results = {"success": 0, "failed": 0, "skipped": 0}
        
        for file_path in self.files_to_sync:
            result = self.sync_file(file_path)
            if result:
                results["success"] += 1
            else:
                results["failed"] += 1
        
        print(f"📊 Результат: {results['success']} успешно, {results['failed']} ошибок")
        
        # Если есть ошибки, пробуем повторно через 30 секунд
        if results["failed"] > 0:
            print("🔄 Повторная попытка через 30 секунд...")
            time.sleep(30)
            
            for file_path in self.files_to_sync:
                self.sync_file(file_path)
    
    def start_auto_sync(self, interval_minutes=10):
        """
        Запускает автоматическую синхронизацию
        
        Args:
            interval_minutes: Интервал в минутах
        """
        if self.is_running:
            print("⚠️  Автосинхронизация уже запущена")
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
        Останавливает автоматическую синхронизацию
        """
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("⏹️  Автосинхронизация остановлена")
    
    def manual_sync(self):
        """
        Ручная синхронизация (можно вызывать по команде)
        """
        print("🔄 Ручная синхронизация...")
        return self.sync_all_files()
