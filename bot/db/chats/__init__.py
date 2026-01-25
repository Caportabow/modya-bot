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

async def migrate_chat(old_chat_id: int, new_chat_id):
    """Мигрирует чат на новый chat_id."""
    await db.execute(
        """
        UPDATE chats
        SET chat_id = $2
        WHERE chat_id = $1
        """, old_chat_id, new_chat_id
    )

async def forget_chat(chat_id: int):
    """Удаляем чат из датабазы."""
    await db.execute(
        """
        DELETE FROM chats
        WHERE chat_id = $1;
        """, chat_id
    )

async def get_all_chat_ids():
    """Получаем айди всех чатов из датабазы."""
    chats = await db.fetchmany(
        """
            SELECT * FROM chats
        """
    )
    return [int(chat['chat_id']) for chat in chats]