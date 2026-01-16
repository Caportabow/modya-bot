from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
import re

class DurationParser:
    """Парсер человеческого времени в машинное."""
    
    # Символы для нормализации латиницы → кириллица
    LATIN_TO_CYRILLIC = {
        'e': 'е', 'E': 'Е', 'p': 'р', 'P': 'Р', 'x': 'х', 'X': 'Х',
        'a': 'а', 'A': 'А', 'o': 'о', 'O': 'О', 'c': 'с', 'C': 'С',
    }
    
    # Ключевые слова для бесконечного времени
    FOREVER_KEYWORDS = frozenset({
        "всё время", "вся", "все время", "навсегда", "вечность",
        "вечно", "постоянно", "навеки"
    })
    
    # Дни недели (0 = понедельник, 6 = воскресенье)
    WEEKDAYS = {
        "понедельник": 0, "пн": 0,
        "вторник": 1, "вт": 1,
        "среда": 2, "ср": 2,
        "четверг": 3, "чт": 3,
        "пятница": 4, "пт": 4,
        "суббота": 5, "сб": 5,
        "воскресенье": 6, "вс": 6,
    }
    
    # Единицы времени для парсинга с числами
    TIME_UNITS = {
        "сек": "seconds", "секунд": "seconds", "секунды": "seconds",
        "мин": "minutes", "минут": "minutes", "минуты": "minutes",
        "ч": "hours", "час": "hours", "часов": "hours", "часа": "hours",
        "дн": "days", "день": "days", "дней": "days", "дня": "days",
        "нед": "weeks", "неделя": "weeks", "недели": "weeks", "недель": "weeks",
        "год": "years", "года": "years", "лет": "years"
    }
    
    # Фиксированные слова без чисел
    FIXED_DURATIONS = {
        "день": timedelta(hours=24),
        "сегодня": timedelta(hours=24),
        "сутки": timedelta(hours=24),
        "неделя": timedelta(weeks=1),
        "месяц": timedelta(days=30),
        "год": timedelta(days=365)
    }

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        """Заменяет латиницу на кириллицу для корректного распознавания."""
        for latin, cyrillic in cls.LATIN_TO_CYRILLIC.items():
            text = text.replace(latin, cyrillic)
        return text.lower().strip()

    @classmethod
    def parse_forever(cls, text: str) -> bool:
        """
        Проверяет, является ли текст выражением 'навсегда'.

        Если это так, возвращает True, иначе False
        """
        return True if text in cls.FOREVER_KEYWORDS else False

    @classmethod
    def _parse_weekday(cls, text: str, reference_time: datetime) -> Optional[timedelta]:
        """Парсит дни недели относительно reference_time."""
        for weekday_name, target_weekday in cls.WEEKDAYS.items():
            pattern = rf"\b{re.escape(weekday_name)}\b"
            if re.search(pattern, text):
                current_weekday = reference_time.weekday()
                days_ahead = (target_weekday - current_weekday) % 7
                
                # Если день сегодня или прошёл, берём следующую неделю
                if days_ahead == 0:
                    days_ahead = 7
                
                return timedelta(days=days_ahead)
        return None

    @classmethod
    def _parse_numeric_duration(cls, text: str) -> Optional[timedelta]:
        """Парсит числовые выражения типа '2ч 30мин' или '3 дня'."""
        matches = re.findall(r"(\d+)\s*([а-яА-Я]+)", text)
        if not matches:
            return None

        duration_kwargs = {"weeks": 0, "days": 0, "hours": 0, "minutes": 0, "seconds": 0}
        years = 0

        for value_str, unit in matches:
            value = int(value_str)
            
            # Ищем соответствующую единицу времени
            for unit_prefix, timedelta_key in cls.TIME_UNITS.items():
                if unit.startswith(unit_prefix):
                    if timedelta_key == "years":
                        years += value
                    else:
                        duration_kwargs[timedelta_key] += value
                    break

        # Конвертируем годы в дни (приблизительно)
        duration_kwargs["days"] += years * 365

        if not any(duration_kwargs.values()):
            return None
        
        return timedelta(**duration_kwargs)

    @classmethod
    def _parse_fixed_duration(cls, text: str) -> Optional[timedelta]:
        """Парсит фиксированные слова без чисел типа 'день', 'неделя'."""
        # Проверяем каждое слово в тексте
        for word in text.split():
            if word in cls.FIXED_DURATIONS:
                return cls.FIXED_DURATIONS[word]
        
        # Проверяем весь текст целиком
        return cls.FIXED_DURATIONS.get(text)

    @classmethod
    def parse(cls, text: str, reference_time: datetime = datetime.now(timezone.utc)) -> Optional[timedelta]:
        """
        Парсит человеческое время в машинное.
        
        Возвращает:
        - timedelta — если удалось распарсить,
        - None — если не удалось определить.
        
        Args:
            text: текст для парсинга
            reference_time: точка отсчёта для дней недели
        """
        normalized_text = cls._normalize_text(text)
        
        # 1. Проверяем дни недели
        weekday_result = cls._parse_weekday(normalized_text, reference_time)
        if weekday_result:
            return weekday_result
        
        # 2. Парсим числовые выражения
        if re.search(r'\d', normalized_text):
            return cls._parse_numeric_duration(normalized_text)
        
        # 3. Парсим фиксированные слова
        return cls._parse_fixed_duration(normalized_text)


class TimedeltaFormatter:
    """Форматирует timedelta в человекочитаемый текст."""
    
    # Сокращения единиц времени
    TIME_UNITS = [
        ("years", "г.", 365),
        ("months", "мес.", 30),
        ("weeks", "нед.", 7),
        ("days", "д.", 1),
    ]
    
    SECOND_UNITS = [
        ("hours", "ч.", 3600),
        ("minutes", "мин.", 60),
        ("seconds", "сек.", 1),
    ]
    
    @staticmethod
    def _calculate_components(total_seconds: int) -> dict[str, int]:
        """Разбивает общее количество секунд на компоненты."""
        days = total_seconds // 86400
        remaining_seconds = total_seconds % 86400
        
        # Разбиваем дни на годы, месяцы, недели, дни
        years = days // 365
        days %= 365
        months = days // 30
        days %= 30
        weeks = days // 7
        days %= 7
        
        # Разбиваем секунды на часы, минуты, секунды
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        seconds = remaining_seconds % 60
        
        return {
            "years": years,
            "months": months,
            "weeks": weeks,
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
        }
    
    @classmethod
    def _get_granularity_level(cls, components: dict[str, int]) -> int:
        """
        Определяет уровень гранулярности для отображения.
        Возвращает индекс наибольшей ненулевой единицы времени.
        """
        all_units = ["years", "months", "weeks", "days", "hours", "minutes", "seconds"]
        
        for level, unit in enumerate(all_units):
            if components[unit] > 0:
                return level
        
        return len(all_units) - 1  # По умолчанию - секунды
    
    @classmethod
    def format(
        cls,
        delta: timedelta,
        suffix: Literal["ago", "future", "none"] = "ago",
        max_units: int = 2,
        zero_text: str = "только что"
    ) -> str:
        """
        Форматирует timedelta в человекочитаемую строку.
        
        Args:
            delta: временной промежуток для форматирования
            suffix: суффикс ('ago' = 'назад', 'future' = 'через', 'none' = без суффикса)
            max_units: максимальное количество отображаемых единиц времени
            zero_text: текст для нулевого промежутка времени
            
        Returns:
            Отформатированная строка, например "2 г. 3 мес. назад"
        """
        total_seconds = int(abs(delta.total_seconds()))
        
        if total_seconds == 0:
            return zero_text
        
        components = cls._calculate_components(total_seconds)
        granularity_level = cls._get_granularity_level(components)
        
        # Формируем части строки с учётом гранулярности
        parts = []
        units_added = 0
        
        # Единицы времени на основе дней
        for unit_name, abbr, _ in cls.TIME_UNITS:
            value = components[unit_name]
            if value > 0 and units_added < max_units:
                parts.append(f"{value} {abbr}")
                units_added += 1
        
        # Единицы времени на основе секунд (показываем только если не добавили единицы выше)
        if units_added < max_units:
            for unit_name, abbr, _ in cls.SECOND_UNITS:
                value = components[unit_name]
                if value > 0 and units_added < max_units:
                    parts.append(f"{value} {abbr}")
                    units_added += 1
        
        if not parts:
            return zero_text
        
        # Добавляем суффикс
        result = " ".join(parts)
        
        if suffix == "ago":
            result += " назад"
        elif suffix == "future":
            result = "через " + result
        
        return result
    
    @classmethod
    def format_precise(
        cls,
        delta: timedelta,
        suffix: Literal["ago", "future", "none"] = "ago",
        minimum_unit: str = "seconds"
    ) -> str:
        """
        Форматирует timedelta с полной точностью (все ненулевые единицы).
        
        Args:
            delta: временной промежуток
            suffix: суффикс ('ago' = 'назад', 'future' = 'через', 'none' = без суффикса)
            minimum_unit: минимальная отображаемая единица
            
        Returns:
            Полная отформатированная строка, например "2 г. 3 мес. 1 нед. 4 д. 5 ч. 30 мин. 15 сек."
        """
        total_seconds = int(abs(delta.total_seconds()))
        
        if total_seconds == 0:
            return "только что"
        
        components = cls._calculate_components(total_seconds)
        
        unit_order = {
            "years": 0, "months": 1, "weeks": 2, "days": 3,
            "hours": 4, "minutes": 5, "seconds": 6
        }
        
        min_index = unit_order.get(minimum_unit, 6)
        
        parts = []
        all_units = cls.TIME_UNITS + cls.SECOND_UNITS
        
        for i, (unit_name, abbr, _) in enumerate(all_units):
            value = components[unit_name]
            if value > 0 and i >= min_index:
                parts.append(f"{value} {abbr}")
        
        if not parts:
            return "только что"
        
        result = " ".join(parts)
        
        if suffix == "ago":
            result += " назад"
        elif suffix == "future":
            result = "через " + result
        
        return result