import re
from datetime import datetime, timezone, timedelta
from collections import Counter

import db
from asyncpg import Connection
from config import RUSSIAN_STOPWORDS


async def get_favorite_word(chat_id: int, user_id: int) -> dict | None:
    # Потоково читаем последние 2000 сообщений
    async with db.transaction() as conn:
        conn: Connection

        count = await conn.fetchval(
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
        
        if not count or count <= 50:
            return None

        # Создаём счётчик
        word_counter = Counter()
        
        async for record in conn.cursor(
            """
            SELECT text
            FROM messages
            WHERE chat_id = $1
            AND sender_user_id = $2
            AND text IS NOT NULL
            AND text != ''
            ORDER BY date DESC
            LIMIT 2000
            """, chat_id, user_id
        ):
            text = record['text']
            words = re.findall(r"\b\w+\b", text.lower())
            words = [w for w in words if w not in RUSSIAN_STOPWORDS]
            word_counter.update(words)

    if not word_counter:
        return None

    most_common_word, word_count = word_counter.most_common(1)[0]
    return {"word": most_common_word, "count": word_count}

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
                SUM(CASE WHEN m.date >= $3 THEN 1 ELSE 0 END) AS month_count,
                MAX(r.valid_until) AS rest   -- активный рест или NULL
            FROM messages m
            LEFT JOIN rests r
                ON r.chat_id = m.chat_id
                AND r.user_id = m.sender_user_id
                AND r.valid_until >= NOW()  -- только текущие активные ресты
            WHERE m.chat_id = $4 
            AND m.sender_user_id = $5;
        """, one_day, one_week, one_month, chat_id, user_id
    )

    if not rows: return None  # пользователь не найден / нет сообщений

    return {
        "first_seen": rows["first_seen"],
        "last_active": rows["last_active"],
        "activity": {
            "day_count": int(rows["day_count"]),
            "week_count": int(rows["week_count"]),
            "month_count": int(rows["month_count"]),
            "total": int(rows["total"])
        },
        "rest": rows["rest"],
    }
