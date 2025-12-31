import db

async def set_max_warns(chat_id: int, max_warns: int):
    """Устанавливаем максимальное количество варнов для чата."""
    await db.execute(
        """
        INSERT INTO chats (chat_id, max_warns)
        VALUES ($1, $2)
        ON CONFLICT(chat_id) DO UPDATE SET max_warns = EXCLUDED.max_warns
        """, chat_id, max_warns
    )

async def get_max_warns(chat_id: int):
    """Получаем максимальное количество варнов для чата."""
    result = await db.fetchval(
        """
        SELECT max_warns FROM chats WHERE chat_id = $1
        """, chat_id
    )
    return result if result is not None else 3
