import db
from datetime import datetime


async def user_leaderboard(chat_id: int, page: int, per_page: int = 20, since: datetime | None = None):
    """
    Возвращает топ пользователей в чате по количеству сообщений.
    """
    # Pagination
    limit = per_page + 1 # Берём на 1 больше, чтобы смотреть есть след. страница или нет
    offset = per_page * (page - 1)

    if since is not None:
        query = """
            SELECT u.user_id, u.nickname, COUNT(m.message_id) AS msg_count
            FROM users u
            LEFT JOIN messages m
                ON u.chat_id = m.chat_id
                AND u.user_id = m.sender_user_id
                AND m.date >= $1
            WHERE u.chat_id = $2
            GROUP BY u.user_id, u.nickname
            ORDER BY msg_count DESC
            LIMIT $3 OFFSET $4;
        """
        rows = await db.fetchmany(query, since, chat_id, limit, offset)
    else:
        query = """
            SELECT u.user_id, u.nickname, COUNT(m.message_id) AS msg_count
            FROM users u
            LEFT JOIN messages m
                ON u.chat_id = m.chat_id
                AND u.user_id = m.sender_user_id
            WHERE u.chat_id = $1
            GROUP BY u.user_id, u.nickname
            ORDER BY msg_count DESC
            LIMIT $2 OFFSET $3;
        """
        rows = await db.fetchmany(query, chat_id, limit, offset)
        
    if rows:  # проверяем, что список не пуст
        if len(rows) == limit:
            rows = rows[:-1]  # убираем последний элемент, т.к он часть след. страницы
            next_page = page + 1
        else:
            next_page = None

    data = {
        "data": [{
            "user_id": int(row["user_id"]),
            "nickname": str(row["nickname"]),
            "count": int(row["msg_count"])
        }for row in rows],
        "pagination": {
            "next_page": next_page,
            "prev_page": page-1 if page > 1 else None,
        }
    } if rows else None

    return data
