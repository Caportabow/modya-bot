import db

from datetime import datetime, timezone


async def add_message(message_id:int, chat_id: int, sender_user_id: int, date: datetime,
                      name: str, text: str, forward_user_id: int | None = None,
                      file_id: str | None = None):
    """Добавляем сообщение пользователя в чате."""
    await db.execute(
        """
        INSERT INTO messages(message_id, chat_id, sender_user_id, date, forward_user_id, name, text, file_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, message_id, chat_id, sender_user_id, datetime.fromtimestamp(date, timezone.utc),
        forward_user_id, name, text, file_id
    )

async def get_next_messages(chat_id: int, message_id: int, limit: int = 5):
    rows = await db.fetchmany(
        """
        SELECT sender_user_id, forward_user_id, name, text, file_id
        FROM messages
        WHERE chat_id = $1 AND message_id > $2
        ORDER BY message_id ASC
        LIMIT $3;
        """,
        chat_id, message_id, limit
    )
    return [
        {
            "user_id": r['sender_user_id'],
            "forward_user_id": r['forward_user_id'],
            "name": r['name'],
            "text": r['text'],
            "file_id": r['file_id']
        } for r in rows
    ]

async def plot_user_activity(chat_id: int, user_id: int):
    rows = await db.fetchmany(
        """
            SELECT
                date::date AS day,
                COUNT(*) AS count
            FROM messages
            WHERE chat_id = $1 AND sender_user_id = $2
            GROUP BY day
            ORDER BY day
            LIMIT 365;
        """, chat_id, user_id
    )
    return rows

async def count_messages(chat_id: int, user_id: int, since: int | None = None):
    """Считаем количество сообщений пользователя в чате (если since=None → за всё время)."""
    from_period = since is not None
    args = [chat_id, user_id] + ([since] if from_period else [])
    
    message_quantity = await db.count(
        f"""
        SELECT COUNT(*)
        FROM messages
        WHERE chat_id = $1
        AND sender_user_id = $2{ 'AND date >= $3' if from_period else ''}
        """, *args
    )
    
    return message_quantity or 0
