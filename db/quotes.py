import db

async def add_quote(chat_id: int, sticker_id: str):
    """Добавляем цитату (стикер) пользователя в чате."""
    await db.execute(
        """
        INSERT INTO quotes (chat_id, sticker_file_id)
        VALUES ($1, $2)
        ON CONFLICT(sticker_file_id) DO NOTHING
        """, chat_id, sticker_id
    )

async def get_random_quote(chat_id: int) -> str | None:
    """Возвращает случайную цитату (стикер) в чате."""
    quote = await db.fetchval(
        """
        SELECT sticker_file_id FROM quotes
        WHERE chat_id = $1
        ORDER BY RANDOM()
        LIMIT 1
        """, chat_id
    )

    return quote
