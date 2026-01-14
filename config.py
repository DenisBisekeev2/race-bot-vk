# [file name]: config.py
import os
import json

# Токен бота VK
BOT_TOKEN = os.getenv('BOT_TOKEN', 'vk1.a.QL9trem3ZOHejiUTbdVRlc4M5gpRL5mU6OFMr6HPaIFfClqb4E3dwNRyYy83H8RuIbA1e0rNh9vMVY4LmuSuSdAgrnGOCevbFnXNSq9jiVT_H_T-2e_oGB3ySvaZ_jx9ZCXU23rZRAnydDjOR_JnkVCJQK62AMOlRWCJi-YWJRvYyHCXEUrVrj80HZhTV0zSfzl0u3z-3UkhUor_CFQCWA')
admins_ids = [819016396, 761815201]

# Вебхук настройки
CONFIRMATION_TOKEN = "f9691f4b"
SECRET_KEY = "gonkaWow"
GROUP_ID = 233724428

# Настройки гонок
RACE_DISTANCE = 1000
GLOBAL_RACE_DISTANCE = 1500
MAX_PLAYERS = 10
MAX_PREMIUM_PLAYERS = 15
MIN_PLAYERS = 2
UPDATE_INTERVAL = 2
GLOBAL_RACE_TIMEOUT = 900

# Награды за уровни
LEVEL_REWARD = 500


# Google Sheets настройки
GOOGLE_SHEET_ID = "1uQ1Vezfo85ypSl8vOBdzSCZN7Ueqp11PmSog7TVC3F8"  # Берешь из URL таблицы
GOOGLE_CREDENTIALS = "google_credentials.json"  # Файл с ключами
