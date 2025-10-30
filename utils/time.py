import time
from datetime import timedelta

DAY = 86400
WEEK = 7 * DAY
MONTH = 30 * DAY
YEAR = 365 * DAY
ALL_TIME = None

periods = {
    "day": ["день", "сегодня", "сутки"],
    "week": ["неделя"],
    "month": ["месяц"],
    "year": ["год",],
    "all": ["вся", "весь", "всё время"],
}

def get_since(period: str):
    now = int(time.time())
    if period.lower() in periods["day"]:
        return now - DAY, "сегодня"
    elif period.lower() in periods["week"]:
        return now - WEEK, "неделю"
    elif period.lower() in periods["month"]:
        return now - MONTH, "месяц"
    elif period.lower() in periods["year"]:
        return now - YEAR, "год"
    elif period.lower() in periods["all"]:
        return ALL_TIME, "всё время"
    else:
        raise ValueError("Unknown period")

def format_timedelta(delta: timedelta) -> str:
        seconds = int(delta.total_seconds())
        if seconds <= 1:
            return "только что"
        elif seconds <= 60:
            return f"{seconds} сек. назад"
        elif seconds <= 3600:
            return f"{seconds//60} мин. назад"
        elif seconds <= 86400:
            return f"{seconds//3600} ч. назад"
        else:
            return f"{delta.days} дн. назад"
        