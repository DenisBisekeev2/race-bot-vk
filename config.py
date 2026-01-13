# [file name]: config.py
import os
import json

# Токен бота VK
BOT_TOKEN = os.getenv('BOT_TOKEN', 'vk1.a.MTzBXxQQyLu72tOMdVYarZLJ3yOOmHXJ2d-MIyWIw55LLJnAryrh1ueQTmh7lsmNXYYyLaU8c59brz9S2gBZ1YK_5HYujr809X2mn7N8OlHwOGiIVOzRJJQ1f_9tjsCquwGdHcKKBQ94Bx1TjKl3hQOX0iLel_1FNwgJ7ycrrK2efdNyrdXlqb31SpXpFk_ChGJDWnLnU6moOlIsVKQvtA')
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
  "apiKey": "AIzaSyC7ct-SFUjPC9qJNhhouNiXNR_1mETftbw",
  "authDomain": "racebotvk.firebaseapp.com",
  "projectId": "racebotvk",
  "storageBucket": "racebotvk.firebasestorage.app",
  "messagingSenderId": "365558962198",
  "appId": "1:365558962198:web:f552fdb300c29624953d37",
  "measurementId": "G-CQ93R5VJ5N"
}

# Данные для аутентификации Firebase
FIREBASE_EMAIL = os.getenv('FIREBASE_EMAIL', 'bisekeevdenis6@gmail.com')
FIREBASE_PASSWORD = os.getenv('FIREBASE_PASSWORD', '1234679SeGa')
FIREBASE_SERVICE_ACCOUNT = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT', '{}'))
