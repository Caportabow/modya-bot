import db

async def upsert_command(chat_id: int, user_id: int, command: str, emoji: str, action: str):
    """Добавит РП команду пользователю в чате в ДБ."""
    await db.execute(
        """
        INSERT INTO rp_commands (chat_id, user_id, command, emoji, action)
        VALUES ($1, $2, $3, $4, $5)
        """,
        chat_id, user_id, command.lower(), emoji, action
    )

async def delete_rp_command(chat_id: int, user_id: int, command: str):
    """Удалит РП команду пользователя в чате из ДБ."""
    commands = await db.fetchmany(
        """
        DELETE FROM rp_commands
        WHERE chat_id = $1 AND user_id = $2 AND command = $3
        RETURNING chat_id, user_id;
        """, chat_id, user_id, command.lower()
    )
    
    return (commands and len(commands) > 0)

async def count_user_commands(chat_id: int, user_id: int) -> int:
    """Возвращает количество РП команд пользователя в чате."""
    cmd_count = await db.count(
        """
        SELECT COUNT(*)
        FROM rp_commands
        WHERE chat_id = $1
        AND user_id = $2;
        """, chat_id, user_id
    )
    return cmd_count or 0

async def get_user_rp_commands(chat_id: int, user_id: int) -> dict | None:
    """Возвращает список РП команд пользователя в чате."""
    rows = await db.fetchmany(
        """
        SELECT command, emoji, action
        FROM rp_commands
        WHERE chat_id = $1 AND user_id = $2;
        """, chat_id, user_id
    )

    return {row['command']: f"{row['emoji']} • {{trigger}} {row['action']} {{target}}" for row in rows} if rows else None
