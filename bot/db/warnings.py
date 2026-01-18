import db
from asyncpg import Connection
from datetime import datetime, timezone
from typing import Optional


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

async def get_user_warnings(chat_id: int, user_id: int, page: int, per_page: int = 10) -> Optional[dict]:
    """Возвращает список варнов пользователя в чате."""
    # Pagination
    limit = per_page + 1 # Берём на 1 больше, чтобы смотреть есть след. страница или нет
    offset = per_page * (page - 1)

    rows = await db.fetchmany(
        """
        SELECT administrator_user_id, assignment_date, reason, expire_date
        FROM warnings
        WHERE chat_id = $1 AND user_id = $2
        ORDER BY assignment_date ASC
        LIMIT $3 OFFSET $4;
        """, chat_id, user_id, limit, offset
    )
    if rows:  # проверяем, что список не пуст
        if len(rows) == limit:
            rows = rows[:-1]  # убираем последний элемент, т.к он часть след. страницы
            next_page = page + 1
        else:
            next_page = None
    
    data = {
        "data": [{   
            "administrator_user_id": int(row['administrator_user_id']),
            "assignment_date": row['assignment_date'],
            "reason": row['reason'],
            "expire_date": row['expire_date']
        } for row in rows],
        "pagination": {
            "next_page": next_page,
            "prev_page": page-1 if page > 1 else None,
        }
    } if rows else None

    return data

async def get_all_warnings(chat_id: int, page: int, per_page: int = 20) -> Optional[dict]:
    """Возвращает список пользователей с варнами в чате."""
    # Pagination
    limit = per_page + 1 # Берём на 1 больше, чтобы смотреть есть след. страница или нет
    offset = per_page * (page - 1)

    rows = await db.fetchmany(
        """
        SELECT user_id, COUNT(*) AS warning_count
        FROM warnings
        WHERE chat_id = $1
        GROUP BY user_id
        ORDER BY warning_count DESC
        LIMIT $2 OFFSET $3;
        """, chat_id, limit, offset
    )
    if rows:  # проверяем, что список не пуст
        if len(rows) == limit:
            rows = rows[:-1]  # убираем последний элемент, т.к он часть след. страницы
            next_page = page + 1
        else:
            next_page = None

    data = {
        "data": [{   
            "user_id": int(row['user_id']),
            "count": int(row['warning_count']),
        } for row in rows],
        "pagination": {
            "next_page": next_page,
            "prev_page": page-1 if page > 1 else None,
        }
    } if rows else None

    return data

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
