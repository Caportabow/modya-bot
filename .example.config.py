import json

# Values
TOKEN = "YOUR BOT TOKEN HERE" # @BotFather in Telegram
API_ID = 12345 # my.telegram.org
API_HASH = "YOUR API HASH HERE" # my.telegram.org

# Production
PRODUCTION = True # (ON/OFF)
DEVELOPERS_ID = [] # (Telegram user IDs)

# Pictures
HELLO_PICTURE_ID = "AgACAgIAAyEGAAS7wxNHAANAaPrGTWcs7T0JzbfL8UzY_aqOyg0AAgbxMRuZh9lL7mXuJTHRdj8BAAMCAAN3AAM2BA"

# Modules
DATABASE_URL = "postgresql://user:password@localhost:5432/dbname"

with open("resources/russian_stopwords.json", "r", encoding="utf-8") as f:
    RUSSIAN_STOPWORDS = set(json.load(f))
