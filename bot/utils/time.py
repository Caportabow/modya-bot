from datetime import timedelta, datetime, timezone

periods = {
    "day": ["день", "сегодня", "сутки"],
    "week": ["неделя"],
    "month": ["месяц"],
    "year": ["год",],
    "all": ["вся", "весь", "всё время"],
}

def get_since(period: str):
    now = datetime.now(timezone.utc)
    one_day = now - timedelta(days=1)
    one_week = now - timedelta(days=7)
    one_month = now - timedelta(days=30)
    one_year = now - timedelta(days=365)
    all_time = None

    if period.lower() in periods["day"]:
        return one_day, "сегодня"
    elif period.lower() in periods["week"]:
        return one_week, "неделю"
    elif period.lower() in periods["month"]:
        return one_month, "месяц"
    elif period.lower() in periods["year"]:
        return one_year, "год"
    elif period.lower() in periods["all"]:
        return all_time, "всё время"
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
        