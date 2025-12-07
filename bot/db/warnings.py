import db
from asyncpg import Connection
from datetime import datetime, timezone


async def add_warning(chat_id: int, user_id: int, admin_user_id: int, reason: str | None, expire_date: datetime | None) -> int | None:
    """Добавляет варн пользователю в чате."""
    async with db.transaction() as conn:
        conn: Connection

        await conn.execute(
            """
            INSERT INTO warnings(chat_id, user_id, administrator_user_id, assignment_date, reason, expire_date)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            chat_id, user_id, admin_user_id, datetime.now(timezone.utc), reason, expire_date
        )

        # Считаем количество варнов после добавления
        count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM warnings
            WHERE chat_id = $1 AND user_id = $2
            """, chat_id, user_id
        )

    return count

async def get_user_warnings(chat_id: int, user_id: int) -> list[dict]:
    """Возвращает список варнов пользователя в чате."""
    rows = await db.fetchmany(
        """
        SELECT administrator_user_id, assignment_date, reason, expire_date
        FROM warnings
        WHERE chat_id = $1 AND user_id = $2
        ORDER BY assignment_date ASC;
        """, chat_id, user_id
    )

    return [
        {   
            "administrator_user_id": row['administrator_user_id'],
            "assignment_date": row['assignment_date'],
            "reason": row['reason'],
            "expire_date": row['expire_date']
        }
        for row in rows
    ]

async def get_all_warnings(chat_id: int) -> list[dict]:
    """Возвращает список пользователей с варнами в чате."""
    rows = await db.fetchmany(
        """
        SELECT user_id, COUNT(*) AS warning_count
        FROM warnings
        WHERE chat_id = $1
        GROUP BY user_id
        ORDER BY warning_count DESC;
        """, chat_id
    )

    return [
        {   
            "user_id": row['user_id'],
            "count": row['warning_count'],
        }
        for row in rows
    ]

async def remove_warning(chat_id: int, user_id: int,
                        warn_index: int | None = None) -> bool:
    """Удаляет варн пользователя в чате по индексу (None - последний варн).
                            Возвращает True, если удаление прошло успешно."""
    is_indexed = warn_index is not None
    args = [chat_id, user_id] + ([warn_index] if is_indexed else [])

    warn_id = await db.fetchval(
        f"""
        SELECT id FROM warnings
        WHERE chat_id = $1 AND user_id = $2
        ORDER BY assignment_date {'ASC' if is_indexed else 'DESC'}
        LIMIT 1{' OFFSET $3' if is_indexed else ''}
        """,
        *args
    )

    if not warn_id: return False  # Варн с таким индексом не найден

    await db.execute(
        "DELETE FROM warnings WHERE id = $1",
        warn_id
    )

    return True

async def amnesty(chat_id: int):
    await db.execute(
        "DELETE FROM warnings WHERE chat_id = $1",
        chat_id
    )

async def expire_warnings():
    await db.execute(
        "DELETE FROM warnings WHERE expire_date IS NOT NULL AND expire_date <= $1",
        datetime.now(timezone.utc)
    )
