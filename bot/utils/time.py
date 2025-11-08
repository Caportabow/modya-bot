import re
from datetime import timedelta


def get_duration(text: str) -> timedelta | str | None:
    """
        Парсит человеческое время в машинное.
        Возвращает:
        - timedelta — если удалось распарсить,
        - "forever" — если пользователь указал бесконечное время,
        - None — если не удалось определить.
    """
    def normalize_russian_text(text: str) -> str:
        replacements = {
            'e': 'е', 'E': 'Е', 'p': 'р', 'P': 'Р', 'x': 'х', 'X': 'Х',
            'a': 'а', 'A': 'А', 'o': 'о', 'O': 'О', 'c': 'с', 'C': 'С',
        }
        for latin, cyrillic in replacements.items():
            text = text.replace(latin, cyrillic)
        return text

    text = normalize_russian_text(text.lower().strip())

    # Проверяем на "всё время" и подобные выражения
    forever_words = {
        "всё время", "вся", "все время", "навсегда", "вечность",
        "вечно", "постоянно", "навеки"
    }
    if text in forever_words:
        return "forever"

    if re.search(r'\d', text):
        units = {
            "сек": "seconds", "секунд": "seconds", "секунды": "seconds",
            "мин": "minutes", "минут": "minutes",
            "ч": "hours", "час": "hours", "часов": "hours",
            "дн": "days", "день": "days", "дней": "days", "дня": "days",
            "нед": "weeks", "неделя": "weeks", "недели": "weeks", "недель": "weeks",
        }

        matches = re.findall(r"(\d+)\s*([а-яА-Я]+)", text)
        if not matches:
            return None

        kwargs = {"weeks": 0,"days": 0, "hours": 0, "minutes": 0, "seconds": 0}
        for value, unit in matches:
            value = int(value)
            for key, td_name in units.items():
                if unit.startswith(key):
                    kwargs[td_name] += value
                    break

        return timedelta(**kwargs)
    else:
        fixed_words = {
            "день": timedelta(hours=24),
            "сегодня": timedelta(hours=24),
            "сутки": timedelta(hours=24),
            "неделя": timedelta(weeks=1),
            "месяц": timedelta(days=30),
            "год": timedelta(days=365)
        }
        for w in text.split():
            duration = fixed_words.get(w)
            if duration: return duration

        return fixed_words.get(text)

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
