import db
from datetime import timedelta, time

async def get_all_settings(chat_id: int):
    """Получаем все настройки в чате."""
    result = await db.fetchone(
        """
        SELECT max_warns, cleaning_min_messages, cleaning_max_inactive, cleaning_eligibility_duration, cleaning_lookback, autoclean_enabled, cleaning_time, cleaning_day_of_week
        FROM chats
        WHERE chat_id = $1
        """, chat_id
    )
    
    return result

# --- WARNINGS SETTINGS ---
async def set_max_warns(chat_id: int, max_warns: int):
    """Устанавливаем максимальное количество варнов для чата."""
    await db.execute(
        """
        INSERT INTO chats (chat_id, max_warns)
        VALUES ($1, $2)
        ON CONFLICT(chat_id) DO UPDATE SET max_warns = EXCLUDED.max_warns
        """, chat_id, max_warns
    )

async def get_max_warns(chat_id: int):
    """Получаем максимальное количество варнов для чата."""
    result = await db.fetchval(
        """
        SELECT max_warns
        FROM chats
        WHERE chat_id = $1
        """, chat_id
    )
    return result if result is not None else 3

# --- CLEANING SETTINGS ---
async def set_cleaning_min_messages(chat_id: int, min_messages: int | None):
    """Устанавливаем минимальное кол-во сообщений на чистке в чате."""
    await db.execute(
        """
        INSERT INTO chats (chat_id, cleaning_min_messages)
        VALUES ($1, $2)
        ON CONFLICT(chat_id) DO UPDATE SET cleaning_min_messages = EXCLUDED.cleaning_min_messages
        """, chat_id, min_messages
    )

async def set_cleaning_max_inactive(chat_id: int, duration: timedelta | None):
    """Устанавливаем максимальную длительность неактивности на чистке в чате."""
    await db.execute(
        """
        INSERT INTO chats (chat_id, cleaning_max_inactive)
        VALUES ($1, $2)
        ON CONFLICT(chat_id) DO UPDATE SET cleaning_max_inactive = EXCLUDED.cleaning_max_inactive
        """, chat_id, duration
    )

async def set_cleaning_eligibility_duration(chat_id: int, duration: timedelta = timedelta(days=4)):
    """
    Устанавливаем минимальный возраст пользователя в чате, чтобы участвовать в чистке в чате.
    """
    await db.execute(
        """
        INSERT INTO chats (chat_id, cleaning_eligibility_duration)
        VALUES ($1, $2)
        ON CONFLICT(chat_id) DO UPDATE SET cleaning_eligibility_duration = EXCLUDED.cleaning_eligibility_duration
        """, chat_id, duration
    )

async def set_cleaning_lookback(chat_id: int, lookback: timedelta = timedelta(days=7)):
    """Устанавливаем период просмотра сообщений для чистки в чате."""
    await db.execute(
        """
        INSERT INTO chats (chat_id, cleaning_lookback)
        VALUES ($1, $2)
        ON CONFLICT(chat_id) DO UPDATE SET cleaning_lookback = EXCLUDED.cleaning_lookback
        """, chat_id, lookback
    )

async def enable_auto_cleaning(chat_id: int, day_of_week: int, cleaning_time: time):
    """Планируем регулярную автоматическую чистку."""
    await db.execute(
        """
        INSERT INTO chats (chat_id, cleaning_day_of_week, cleaning_time, autoclean_enabled)
        VALUES ($1, $2, $3, true)
        ON CONFLICT(chat_id) DO UPDATE SET
            cleaning_day_of_week = EXCLUDED.cleaning_day_of_week,
            cleaning_time = EXCLUDED.cleaning_time,
            autoclean_enabled = EXCLUDED.autoclean_enabled
        """, chat_id, day_of_week, cleaning_time
    )

async def disable_auto_cleaning(chat_id: int):
    """Отключаем автоматическую чистку."""
    await db.execute(
        """
        INSERT INTO chats (chat_id, autoclean_enabled)
        VALUES ($1, false)
        ON CONFLICT(chat_id) DO UPDATE SET
            autoclean_enabled = EXCLUDED.autoclean_enabled
        """, chat_id
    )
