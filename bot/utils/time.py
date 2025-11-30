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
            "год": "years", "года": "years", "лет": "years"
        }

        matches = re.findall(r"(\d+)\s*([а-яА-Я]+)", text)
        if not matches:
            return None

        kwargs = {"weeks": 0, "days": 0, "hours": 0, "minutes": 0, "seconds": 0}
        years = 0

        for value, unit in matches:
            value = int(value)
            for key, td_name in units.items():
                if unit.startswith(key):
                    if td_name == "years":
                        years += value
                    else:
                        kwargs[td_name] += value
                    break

        # Перевод лет в дни (приблизительно)
        kwargs["days"] += years * 365

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
    total_seconds = int(delta.total_seconds())
    days = delta.days
    seconds = total_seconds % 86400

    years = days // 365
    days %= 365
    months = days // 30
    days %= 30
    weeks = days // 7
    days %= 7
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds %= 60

    parts = []
    if years > 0:
        parts.append(f"{years} г.")
    if months > 0 and years == 0:
        parts.append(f"{months} мес.")
    if weeks > 0 and years == 0 and months == 0:
        parts.append(f"{weeks} нед.")
    if days > 0 and years == 0 and months == 0:
        parts.append(f"{days} д.")
    if hours > 0 and years == 0 and months == 0 and weeks == 0:
        parts.append(f"{hours} ч.")
    if minutes > 0 and years == 0 and months == 0 and weeks == 0 and days == 0:
        parts.append(f"{minutes} мин.")
    if seconds > 0 and years == 0 and months == 0 and weeks == 0 and days == 0 and hours == 0:
        parts.append(f"{seconds} сек.")

    return (' '.join(parts) + (" назад" if adder else "")) if parts else "только-что"
