import os
import sys

# Добавляем путь к проекту для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import GITHUB_API_KEY

# Конфигурация GitHub
GITHUB_REPO = "DenisBisekeev2/race-bot-vk"  # Например: "denis123/gonka-bot"

# Файлы для синхронизации (пути относительно корня проекта)
FILES_TO_SYNC = [
    "users.json",
    "chats.json",
    "admin.json",
    "payments.json"  # Добавьте другие файлы при необходимости
]

# Интервал синхронизации (в минутах)
SYNC_INTERVAL = 10  # Каждые 10 минут
