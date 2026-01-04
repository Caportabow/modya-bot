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

async def export_rp_commands(old_chat_id: int, user_id: int, new_chat_id: int, max_limit: int) -> list[str]:
    """
    Экспортирует команды одной транзакцией с проверкой лимита внутри БД.
    Возвращает количество добавленных команд или 0, если лимит превышен.
    """
    query = """
    WITH current_data AS (
        -- Считаем, сколько команд уже есть в целевом чате
        SELECT count(*) as total_now FROM rp_commands 
        WHERE chat_id = $3 AND user_id = $2
    ),
    to_be_added AS (
        -- Находим команды из старого чата, которых НЕТ в новом
        SELECT command, emoji, action 
        FROM rp_commands 
        WHERE chat_id = $1 AND user_id = $2
        AND command NOT IN (
            SELECT command FROM rp_commands WHERE chat_id = $3 AND user_id = $2
        )
    ),
    check_limit AS (
        -- Проверяем: (текущие + новые) <= лимит
        SELECT EXISTS (
            SELECT 1 FROM current_data 
            WHERE total_now + (SELECT count(*) FROM to_be_added) <= $4
        ) as can_insert
    )
    INSERT INTO rp_commands (chat_id, user_id, command, emoji, action)
    SELECT $3, $2, command, emoji, action
    FROM to_be_added
    WHERE (SELECT can_insert FROM check_limit) = TRUE
    RETURNING command;
    """

    rows = await db.fetchmany(query, old_chat_id, user_id, new_chat_id, max_limit)
    return [row['command'] for row in rows] if rows else []
