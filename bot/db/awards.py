import db
from datetime import datetime, timezone


async def add_award(chat_id: int, user_id: int, giver_user_id: int, award: str) -> int | None:
    """Добавляет награду пользователю в чате."""
    await db.execute(
        """
        INSERT INTO awards(chat_id, user_id, giver_user_id, assignment_date, award)
        VALUES ($1, $2, $3, $4, $5)
        """,
        chat_id, user_id, giver_user_id, datetime.now(timezone.utc), award
    )

    # Считаем количество варнов после добавления
    count = await db.count(
        """
        SELECT COUNT(*)
        FROM awards
        WHERE chat_id = $1 AND user_id = $2
        """, chat_id, user_id
    )
    return count

async def get_awards(chat_id: int, user_id: int) -> list[dict]:
    """Возвращает список наград пользователя в чате."""
    rows = await db.fetchmany(
        """
        SELECT giver_user_id, assignment_date, award
        FROM awards
        WHERE chat_id = $1 AND user_id = $2
        ORDER BY assignment_date ASC;
        """, chat_id, user_id
    )

    return [
        {   
            "giver_user_id": row['giver_user_id'],
            "assignment_date": row['assignment_date'],
            "award": row['award']
        }
        for row in rows
    ]

async def remove_award(chat_id: int, user_id: int,
                        award_index: int | None = None) -> bool:
    """Удаляет награду пользователя в чате по индексу (None - последняя награда).
                            Возвращает True, если удаление прошло успешно."""
    is_indexed = award_index is not None
    args = [chat_id, user_id] + ([award_index] if is_indexed else [])

    award_id = await db.fetchval(
        f"""
        SELECT id FROM awards
        WHERE chat_id = $1 AND user_id = $2
        ORDER BY assignment_date {'ASC' if is_indexed else 'DESC'}
        LIMIT 1{' OFFSET $3' if is_indexed else ''}
        """,
        *args
    )

    if not award_id: return False  # Варн с таким индексом не найден

    await db.execute(
        "DELETE FROM awards WHERE id = $1",
        award_id
    )

    return True
