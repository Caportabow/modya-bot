import db
from datetime import datetime, timezone, timedelta

async def minmsg_users(chat_id: int, min_messages: int) -> list[dict] | None:
    """
    Возвращает список пользователей, у которых сообщений меньше, чем требуется
    (анализ за последние 7 дней, при условии, что с первого сообщения прошло ≥ 4 дней).
    """
    now_dt = datetime.now(timezone.utc)
    cutoff_date = now_dt - timedelta(days=7) # последние 7 дней
    min_activity_age = now_dt - timedelta(days=4) # минимум 4 дня с первого сообщения

    query = """
        SELECT m.sender_user_id, COUNT(*) AS message_count
        FROM messages m
        WHERE m.chat_id = $1
          AND m.date >= $2
          AND (
              SELECT MIN(date)
              FROM messages
              WHERE chat_id = m.chat_id AND sender_user_id = m.sender_user_id
          ) <= $3
        GROUP BY m.sender_user_id
        HAVING COUNT(*) < $4
        ORDER BY message_count ASC
    """

    rows = await db.fetchmany(query, chat_id,
            cutoff_date, min_activity_age, min_messages
    )

    return [
        {
            "user_id": row["sender_user_id"],
            "count": row["message_count"]
        } for row in rows
    ] if rows else None
