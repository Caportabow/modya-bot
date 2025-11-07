import re
from datetime import datetime, timezone, timedelta
from collections import Counter

import db
from utils.time import format_timedelta
from config import RUSSIAN_STOPWORDS


async def get_favorite_word(chat_id: int, user_id: int) -> dict | None:
    count = await db.count(
        """
        SELECT COUNT(*)
        FROM messages
        WHERE chat_id = $1
        AND sender_user_id = $2
        AND text IS NOT NULL
        AND TRIM(text) != ''
        """,
        chat_id,
        user_id
    )
    if count and count <= 50:
        return None

    # Создаём счётчик
    word_counter = Counter()

    # Потоково читаем сообщения
    async with db.connection() as conn:
        async with conn.transaction():
            async for record in conn.cursor(
                """
                SELECT text
                FROM messages
                WHERE chat_id = $1
                AND sender_user_id = $2
                AND text IS NOT NULL
                AND TRIM(text) != ''
                ORDER BY date
                LIMIT 300
                """, chat_id, user_id
            ):
                text = record['text']
                words = re.findall(r"\b\w+\b", text.lower())
                words = [w for w in words if w not in RUSSIAN_STOPWORDS]
                word_counter.update(words)

    if not word_counter:
        return None

    most_common_word, count = word_counter.most_common(1)[0]
    return {"word": most_common_word, "count": count}

async def user_stats(chat_id: int, user_id: int):
    now_dt = datetime.now(timezone.utc)
    one_day = now_dt - timedelta(days=1)
    one_week = now_dt - timedelta(days=7)
    one_month = now_dt - timedelta(days=30)

    rows = await db.fetchone(
        """
        SELECT 
            MIN(m.date) AS first_seen,
            MAX(m.date) AS last_active,
            COUNT(m.message_id) AS total,
            SUM(CASE WHEN m.date >= $1 THEN 1 ELSE 0 END) AS day_count,
            SUM(CASE WHEN m.date >= $2 THEN 1 ELSE 0 END) AS week_count,
            SUM(CASE WHEN m.date >= $3 THEN 1 ELSE 0 END) AS month_count
        FROM messages m
        WHERE m.chat_id = $4 AND m.sender_user_id = $5;
        """, one_day, one_week, one_month, chat_id, user_id
    )

    if not rows: return None  # пользователь не найден / нет сообщений

    # преобразуем время в нормальный вид
    first_dt = rows["first_seen"]
    last_dt = rows["last_active"]
    age = now_dt - first_dt
    last_diff = now_dt - last_dt

    # Поиск любимого слова
    fav_word = await get_favorite_word(chat_id, user_id)

    return {
        "first_seen": f"{first_dt:%d.%m.%Y} ({format_timedelta(age)})",
        "last_active": format_timedelta(last_diff),
        "activity": f"{rows["day_count"]} | {rows["week_count"]} | {rows["month_count"]} | {rows["total"]}",
        "favorite_word": fav_word
    }
