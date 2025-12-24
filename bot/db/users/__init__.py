import db


async def upsert_user(chat_id: int, user_id: int, first_name: str, username: str | None = None):
    """Добавит аккаунт пользователя в чате в ДБ."""
    await db.execute(
        """
        INSERT INTO users (chat_id, user_id, username, nickname)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (chat_id, user_id) DO UPDATE
        SET username = EXCLUDED.username;
        """,
        chat_id, user_id, username, first_name
    )

async def remove_user(chat_id: int, user_id: int):
    """Удалит профиль пользователя в чате из ДБ."""
    await db.execute(
        """
        DELETE FROM users
        WHERE chat_id = $1 AND user_id = $2;
        """, chat_id, user_id
    )

async def get_all_users_in_chat(chat_id: int) -> list[int] | None:
    """Возвращает всех пользователей, зарегистрированных в чате."""
    rows = await db.fetchmany(
        """
        SELECT user_id
        FROM users
        WHERE chat_id = $1;
        """, chat_id
    )
    return [row['user_id'] for row in rows] if rows else None

async def get_random_chat_member(chat_id: int) -> int | None:
    """Возвращает рандомного пользователя, из чата."""
    user_id = await db.fetchval(
        """
        SELECT user_id
        FROM users
        WHERE chat_id = $1
        ORDER BY RANDOM()
        LIMIT 1;
        """, chat_id
    )

    return user_id or None

async def get_uid(chat_id: int, username: str) -> int | None:
    """Возвращает user_id пользователя в чате по username."""
    user_id = await db.fetchval(
        """
        SELECT user_id
        FROM users
        WHERE chat_id = $1 AND username ILIKE $2;
        """, chat_id, username
    )

    return user_id
