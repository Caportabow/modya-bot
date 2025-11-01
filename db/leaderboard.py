import db


async def user_leaderboard(chat_id: int, limit: int = 10, since: int | None = None):
    """
    Возвращает топ пользователей в чате по количеству сообщений.
    """
    if since is not None:
        query = """
            SELECT u.user_id, u.nickname, COUNT(m.id) AS msg_count
            FROM users u
            LEFT JOIN messages m
                ON u.chat_id = m.chat_id
                AND u.user_id = m.sender_user_id
                AND m.date >= $1
            WHERE u.chat_id = $2
            GROUP BY u.user_id, u.nickname
            ORDER BY msg_count DESC
            LIMIT $3
        """
        rows = await db.fetchmany(query, since, chat_id, limit)
    else:
        query = """
            SELECT u.user_id, u.nickname, COUNT(m.id) AS msg_count
            FROM users u
            LEFT JOIN messages m
                ON u.chat_id = m.chat_id
                AND u.user_id = m.sender_user_id
            WHERE u.chat_id = $1
            GROUP BY u.user_id, u.nickname
            ORDER BY msg_count DESC
            LIMIT $2
        """
        rows = await db.fetchmany(query, chat_id, limit)

    return [
        {
            "user_id": row["user_id"],
            "nickname": row["nickname"],
            "count": row["msg_count"]
        }
        for row in rows
    ]
