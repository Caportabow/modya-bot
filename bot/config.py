import json
import os

# Values
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# Production / Development
PRODUCTION = True # (ON/OFF)
DEVELOPERS_ID = [2142151597, 6038133594] # (Telegram user IDs)

# Misc
MAX_MESSAGE_LENGTH = 4000  # Максимальная длинна сообщения в Telegram

# Pictures
HELLO_PICTURE_ID = "AgACAgIAAyEGAAS7wxNHAANAaPrGTWcs7T0JzbfL8UzY_aqOyg0AAgbxMRuZh9lL7mXuJTHRdj8BAAMCAAN3AAM2BA"
UPDATE_PICTURE_ID = "AgACAgIAAxkDAAMxaQ4gsrC5pVum6_dHycL1okQkQBcAAnILaxsq9nlIvvkdO3OyZ0UBAAMCAAN3AAM2BA"
MAINTENANCE_PICTURE_ID = "AgACAgIAAxkDAAMyaQ4gsj34QvZ51lF6-YEPTkduRE0AAnMLaxsq9nlI-Mmn3FNq4I4BAAMCAAN3AAM2BA"
MARRIAGES_PICTURE_ID = "AgACAgIAAxkDAAMzaQ4gs5JQlo9jVRqyMDRvW6yw61gAAnQLaxsq9nlI7BTX_e3pOrQBAAMCAAN3AAM2BA"
AWARDS_PICTURE_ID = "AgACAgIAAxkDAAM3aQ4h2VyWuWuHZvawnr6fuVNPSgEAAn4Laxsq9nlILkQ1xmvWIzUBAAMCAAN3AAM2BA"
WARNINGS_PICTURE_ID = "AgACAgIAAxkDAAM4aQ4h2qsd4nqp5LrvZ9CSMpyf2D0AAn8Laxsq9nlIWLKcJyh1sqcBAAMCAAN3AAM2BA"

# Modules
DATABASE_URL = os.getenv("DATABASE_URL", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, "resources", "russian_stopwords.json"), "r", encoding="utf-8") as f:
    RUSSIAN_STOPWORDS = json.load(f)

with open(os.path.join(BASE_DIR, "resources", "rp_commands.json"), "r") as f:
    RP_COMMANDS = json.load(f)

with open(os.path.join(BASE_DIR, "resources", "quote_template.html"), "r", encoding="utf-8") as f:
    QUOTE_TEMPLATE = f.read()

with open(os.path.join(BASE_DIR, "resources", "family_template.html"), "r", encoding="utf-8") as f:
    FAMILY_TEMPLATE = f.read()

with open(os.path.join(BASE_DIR, "resources", "activity_chart.html"), "r", encoding="utf-8") as f:
    ACTIVITY_CHART_TEMPLATE = f.read()

# Limits
MAX_RP_COMMANDS_IN_CHAT_PER_USER = 15
