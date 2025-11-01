import db

async def set_nickname(chat_id: int, user_id: int, nickname: str | None):
    """Меняем кастомный ник пользователя в чате (или убираем)."""
    await db.execute(
        """
        UPDATE users
        SET nickname = $1
        WHERE chat_id = $2
        AND user_id = $3
        """, nickname, chat_id, user_id
    )

async def get_nickname(chat_id: int, user_id: int | None = None) -> str | None:
    """Возвращает nickname пользователя в чате по uid."""
    nickname = await db.fetchval(
        """
        SELECT nickname
        FROM users
        WHERE chat_id = $1
        AND user_id = $2
        """, chat_id, user_id
    )

    return nickname
