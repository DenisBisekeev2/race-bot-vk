import json
import time
import schedule
from github import Github
import os

class GitHubFileUpdater:
    def __init__(self, token, repo_name, branch="main"):
        """
        Инициализация GitHub клиента
        
        Args:
            token: GitHub Personal Access Token
            repo_name: Название репозитория (username/repo)
            branch: Ветка (по умолчанию main)
        """
        self.g = Github(token)
        self.repo = self.g.get_repo(repo_name)
        self.branch = branch
        
    def update_json_file(self, file_path, new_data):
        """
        Обновление JSON файла в репозитории
        
        Args:
            file_path: Путь к файлу в репозитории
            new_data: Новые данные для файла
        """
        try:
            # Получаем содержимое файла
            file_content = self.repo.get_contents(file_path, ref=self.branch)
            
            # Обновляем данные
            updated_content = json.dumps(new_data, ensure_ascii=False, indent=2)
            
            # Обновляем файл
            self.repo.update_file(
                path=file_path,
                message=f"Auto-update: {file_path}",
                content=updated_content,
                sha=file_content.sha,
                branch=self.branch
            )
            print(f"✅ Файл {file_path} успешно обновлен")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обновления {file_path}: {e}")
            return False
    
    def update_multiple_json_files(self, files_data):
        """
        Обновление нескольких JSON файлов
        
        Args:
            files_data: Словарь {путь_к_файлу: данные}
        """
        results = {}
        for file_path, data in files_data.items():
            results[file_path] = self.update_json_file(file_path, data)
        return results

# Пример использования в вашем приложении
def setup_github_updater():
    """
    Настройка автообновления JSON файлов
    """
    # Токен GitHub (нужно создать в настройках GitHub)
    GITHUB_TOKEN = "ваш_github_token"
    REPO_NAME = "DenisBisekeev2"
    
    # Инициализируем обновлятель
    updater = GitHubFileUpdater(GITHUB_TOKEN, REPO_NAME)
    
    def update_all_json_files():
        """Функция для обновления всех JSON файлов"""
        print(f"🔄 Начинаю обновление JSON файлов... {time.ctime()}")
        
        # Пример: обновляем users.json с вашими данными
        users_data = load_data(USERS_DB_FILE)  # ваша функция загрузки
        updater.update_json_file("users.json", users_data)
        
        
        updater.update_json_file("chats.json", load_data(CHATS_DB_FILE))
        updater.update_json_file("admin.json", load_admin_data())
        
        print("✅ Обновление завершено")
    
    return updater, update_all_json_files
