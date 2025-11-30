import db

async def add_chat(chat_id: int):
    """Добавляем чат в датабазу."""
    await db.execute(
        """
        INSERT INTO chats (chat_id)
        VALUES ($1)
        ON CONFLICT(chat_id) DO NOTHING
        """, chat_id
    )

async def forget_chat(chat_id: int):
    """Удаляем чат из датабазы."""
    await db.execute(
        """
        DELETE FROM chats
        WHERE chat_id = $1;
        """, chat_id
    )