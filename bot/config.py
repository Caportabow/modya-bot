import json
import os

# Values
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# Production
PRODUCTION = True # (ON/OFF)
DEVELOPERS_ID = [2142151597] # (Telegram user IDs)

# Pictures
HELLO_PICTURE_ID = "AgACAgIAAyEGAAS7wxNHAANAaPrGTWcs7T0JzbfL8UzY_aqOyg0AAgbxMRuZh9lL7mXuJTHRdj8BAAMCAAN3AAM2BA"

# Modules
DATABASE_URL = os.getenv("DATABASE_URL")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, "resources", "russian_stopwords.json"), "r", encoding="utf-8") as f:
    RUSSIAN_STOPWORDS = json.load(f)

with open(os.path.join(BASE_DIR, "resources", "rp_commands.json"), "r") as f:
    RP_COMMANDS = json.load(f)

with open(os.path.join(BASE_DIR, "resources", "quote_template.html"), "r", encoding="utf-8") as f:
    QUOTE_TEMPLATE = f.read()
