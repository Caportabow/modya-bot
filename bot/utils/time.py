import re
from datetime import timedelta


def get_duration(text: str) -> timedelta | None:
    """
        Парсит человеческое время в машинное.
        Возвращает None если не получилось.
    """
    # Слова с фиксированным значением
    fixed_words = {
        "день": timedelta(hours=24),
        "сегодня": timedelta(hours=24),
        "сутки": timedelta(hours=24),
        "неделя": timedelta(weeks=1),
        "месяц": timedelta(days=30),
        "год": timedelta(days=365)
    }

    text_lower = text.lower().strip()

    # Сначала проверяем полностью совпадающие слова
    if text_lower in fixed_words:
        return fixed_words[text_lower]
    
    # Теперь проверяем полноценные периоды:
    # Поддерживаемые единицы времени
    units = {
        "сек": "seconds",
        "секунд": "seconds",
        "секунды": "seconds",

        "мин": "minutes",
        "минут": "minutes",

        "ч": "hours",
        "час": "hours",
        "часов": "hours",

        "дн": "days",
        "день": "days",
        "дней": "days",
        "дня": "days",

        "нед": "weeks",
        "недели": "weeks",
        "неделя": "weeks",
        "недели": "weeks",
        "недель": "weeks",
    }

    pattern = r"(\d+)\s*([а-яА-Я]+)"
    matches = re.findall(pattern, text.lower())

    if not matches: return None # Совпадений не найдено

    kwargs = {"weeks": 0,"days": 0, "hours": 0, "minutes": 0, "seconds": 0}

    for value, unit in matches:
        value = int(value)
        for key, td_name in units.items():
            if unit.startswith(key):
                kwargs[td_name] += value
                break

    return timedelta(**kwargs)

def format_timedelta(delta: timedelta, adder: bool = True) -> str:
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days} д.")
    if hours > 0:
        parts.append(f"{hours} ч.")
    if minutes > 0 and days == 0:  # показываем минуты только если нет дней
        parts.append(f"{minutes} мин.")
    if seconds > 0 and days == 0 and hours == 0:  # показываем секунды только если нет дней и часов
        parts.append(f"{seconds} сек.")
        
    return (' '.join(parts) + (" назад" if adder else "")) if parts else "только-что"
