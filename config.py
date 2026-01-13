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

# Firebase конфигурация
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyC7ct-SFUjPC9qJNhhouNiXNR_1mETftbw",  # оставляем как есть
    "authDomain": "racebotvk.firebaseapp.com",  # оставляем
    "databaseURL": "https://racebotvk-default-rtdb.europe-west1.firebasedatabase.app",  # ЗАМЕНИ на свой реальный URL!
    "projectId": "racebotvk",  # оставляем
    "storageBucket": "racebotvk.firebasestorage.app",  # оставляем
    "messagingSenderId": "365558962198",  # оставляем
    "appId": "1:365558962198:web:f552fdb300c29624953d37",  # оставляем
    "measurementId": "G-CQ93R5VJ5N"  # оставляем
}

# Данные для аутентификации Firebase
FIREBASE_EMAIL = os.getenv('FIREBASE_EMAIL', 'bisekeevdenis6@gmail.com')
FIREBASE_PASSWORD = os.getenv('FIREBASE_PASSWORD', '1234679SeGa')
FIREBASE_SERVICE_ACCOUNT = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT', '{}'))
