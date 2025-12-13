import db
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
    cutoff_date = now_dt - timedelta(days=7)
    min_activity_age = now_dt - timedelta(days=4)

    query = """
        WITH first_message_dates AS (
            SELECT 
                chat_id, 
                sender_user_id,
                MIN(date) AS first_message_date
            FROM messages
            WHERE chat_id = $2
            GROUP BY chat_id, sender_user_id
        )
        SELECT 
            u.user_id AS sender_user_id,
            COUNT(m.message_id) AS message_count
        FROM users u
        LEFT JOIN messages m
            ON m.sender_user_id = u.user_id
        AND m.chat_id = u.chat_id
        AND m.date >= $3
        LEFT JOIN first_message_dates fmd
            ON fmd.chat_id = u.chat_id
        AND fmd.sender_user_id = u.user_id
        WHERE u.chat_id = $2
        AND (u.rest IS NULL OR u.rest < $1)
        AND (
                fmd.first_message_date IS NULL
                OR fmd.first_message_date <= $4
            )
        GROUP BY u.user_id
        HAVING COUNT(m.message_id) < $5
        ORDER BY message_count DESC;
    """

    rows = await db.fetchmany(
        query,
        now_dt,
        chat_id,
        cutoff_date,
        min_activity_age,
        min_messages
    )
    
    return [{
        "user_id": int(row["sender_user_id"]),
        "count": int(row["message_count"])
    } for row in rows] if rows else None

async def inactive_users(chat_id: int, duration: timedelta):
    """
    Возвращает пользователей, которые есть в таблице users,
    раньше писали сообщения, но не писали за указанный период.
    Для каждого пользователя указывается дата его последнего сообщения.
    """
    now_dt = datetime.now(timezone.utc)
    since = now_dt - duration

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
            AND (u.rest IS NULL OR u.rest < $2)
        GROUP BY u.user_id
        HAVING 
            COALESCE(MAX(m.date), '1970-01-01') < $3
        ORDER BY last_message_date ASC;
    """

    rows = await db.fetchmany(query, chat_id, now_dt, since)

    return [
        {
            "user_id": int(row["user_id"]),
            "last_message_date": row["last_message_date"]
        }
        for row in rows
    ]
