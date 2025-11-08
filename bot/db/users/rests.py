import db
from datetime import datetime, timezone
from utils.time import format_timedelta

async def get_all_rests(chat_id:int) -> list[dict] | None:
    """Возвращает все активные ресты в чате."""
    now = datetime.now(timezone.utc)
    rests = await db.fetchmany(
        """
        SELECT user_id, rest
        FROM users
        WHERE chat_id = $1
        AND rest IS NOT NULL
        AND rest > $2
        """, chat_id, now
    )

    return [
        {
            'user_id': r['user_id'],
            'rest': f"до {r['rest']:%d.%m.%Y} (еще {format_timedelta(r['rest'] - now, adder=False)})"
        } for r in rests
    ] if rests else None

async def set_rest(chat_id: int, user_id: int, date: datetime | None):
    """Добавляем (или убираем) рест пользователю в чате."""
    await db.execute(
        """
        UPDATE users
        SET rest = $1
        WHERE chat_id = $2
        AND user_id = $3
        """, date, chat_id, user_id
    )

async def verify_rests() -> list[dict] | None:
    """Сбрасывает rest у всех пользователей, у которых дата истекла, и возвращает их список."""
    now = datetime.now(timezone.utc)

    # Обновляем всех сразу и возвращаем тех, у кого rest был сброшен
    rows = await db.fetchmany(
        """
        UPDATE users
        SET rest = NULL
        WHERE rest IS NOT NULL
        AND rest <= $1
        RETURNING chat_id, user_id
        """,
        now
    )

    # Преобразуем в список словарей
    return [{'chat_id': r['chat_id'], 'user_id': r['user_id']} for r in rows] if rows else None

async def get_rest(chat_id: int, user_id: int) -> str | None:
    """Возвращает информацию об рест пользователя в чате по uid."""
    now = datetime.now(timezone.utc)
    rest = await db.fetchval(
        """
        SELECT rest
        FROM users
        WHERE chat_id = $1
        AND user_id = $2
        AND rest > $3
        """, chat_id, user_id, now
    )

    return f"до {rest:%d.%m.%Y} (еще {format_timedelta(rest - now, adder=False)})" if rest else None
