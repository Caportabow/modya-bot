import db
from utils.time import format_timedelta
from datetime import datetime, timezone, timedelta

async def verify_cleaning_possibility(chat_id: int) -> bool:
    """
    Проверяет возможность проведения чистки в чате.
    Возвращает True если чистку уже можно провести, иначе False.
    """
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    query = """
    SELECT
        CASE
            WHEN MIN(date) <= $1 THEN TRUE
            ELSE FALSE
        END AS week_passed
    FROM messages
    WHERE chat_id = $2;
    """
    cleaning_possibility = await db.case(query, week_ago, chat_id)

    return cleaning_possibility

async def minmsg_users(chat_id: int, min_messages: int):
    """
    Возвращает список пользователей, у которых сообщений меньше, чем требуется
    (анализ за последние 7 дней, при условии, что с первого сообщения прошло ≥ 4 дней).
    """
    now_dt = datetime.now(timezone.utc)
    cutoff_date = now_dt - timedelta(days=7) # последние 7 дней
    min_activity_age = now_dt - timedelta(days=4) # минимум 4 дня с первого сообщения

    query = f"""
        SELECT m.sender_user_id, COUNT(*) AS message_count
        FROM messages m
        INNER JOIN users u 
            ON u.user_id = m.sender_user_id
            AND u.chat_id = m.chat_id
        WHERE m.chat_id = $1
        AND m.date >= $2
        AND (
            SELECT MIN(date)
            FROM messages
            WHERE chat_id = m.chat_id AND sender_user_id = m.sender_user_id
        ) <= $3
        GROUP BY m.sender_user_id
        HAVING COUNT(*) < $4
        ORDER BY message_count DESC;
    """

    rows = await db.fetchmany(query, chat_id, cutoff_date,
            min_activity_age, min_messages)

    return [{
            "user_id": row["sender_user_id"],
            "count": row["message_count"]
        } for row in rows ] if rows else None

async def inactive_users(chat_id: int, duration: timedelta):
    """
    Возвращает пользователей, которые есть в таблице users,
    раньше писали сообщения, но не писали за указанный период.
    Для каждого пользователя указывается дата его последнего сообщения.
    """
    since = datetime.now() - duration

    query = """
        SELECT 
            u.user_id,
            MAX(m.date) AS last_message_date
        FROM users u
        LEFT JOIN messages m
            ON m.chat_id = u.chat_id
            AND m.sender_user_id = u.user_id
        WHERE 
            u.chat_id = $1
        GROUP BY u.user_id
        HAVING 
            COALESCE(MAX(m.date), '1970-01-01') < $2
        ORDER BY last_message_date ASC;
    """

    rows = await db.fetchmany(query, chat_id, since)

    now_dt = datetime.now(timezone.utc)
    return [
        {
            "user_id": int(row["user_id"]),
            "last_message_date": format_timedelta(now_dt - row["last_message_date"]) if row["last_message_date"] else "никогда"
        }
        for row in rows
    ]