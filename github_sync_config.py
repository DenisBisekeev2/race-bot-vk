import os

# Импортируем токен из config.py
try:
    from config import GITHUB_API_KEY
except ImportError:
    print("❌ Не найден config.py с GITHUB_API_KEY")
    GITHUB_API_KEY = ""

# ⚠️ УКАЖИТЕ ВАШ РЕПОЗИТОРИЙ!
# Формат: username/repository-name
GITHUB_REPO = "DenisBisekeev2/race-bot-vk"  # <-- ИЗМЕНИТЕ НА СВОЙ!

# Файлы для синхронизации
FILES_TO_SYNC = [
    "users.json",
    "chats.json",
    "admin.json",
    "payments.json",
]

# Интервал синхронизации (в минутах)
SYNC_INTERVAL = 10

# Ветка Git
GITHUB_BRANCH = "main"
