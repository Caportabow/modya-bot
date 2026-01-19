import db
from datetime import datetime, timezone

async def get_all_rests(chat_id:int, page: int, per_page: int = 20) -> list[dict] | None:
    """Возвращает все активные ресты в чате."""
    # Pagination
    limit = per_page + 1 # Берём на 1 больше, чтобы смотреть есть след. страница или нет
    offset = per_page * (page - 1)

    now = datetime.now(timezone.utc)
    rests = await db.fetchmany(
        """
        SELECT user_id, valid_until
        FROM rests
        WHERE chat_id = $1
        AND valid_until > $2
        LIMIT $3 OFFSET $4;
        """, chat_id, now, limit, offset
    )
    
    if rests:  # проверяем, что список не пуст
        if len(rests) == limit:
            rests = rests[:-1]  # убираем последний элемент, т.к он часть след. страницы
            next_page = page + 1
        else:
            next_page = None

    data = {
        "data": [{
            'user_id': int(r['user_id']),
            'valid_until': r['valid_until'],
        } for r in rests],
        "pagination": {
            "next_page": next_page,
            "prev_page": page-1 if page > 1 else None,
        }
    } if rests else None

    return data

async def add_rest(chat_id: int, user_id: int, administrator_user_id: int, valid_until: datetime):
    """Добавляем рест пользователю в чате."""
    now = datetime.now(timezone.utc)
    await db.execute(
        """
        -- Добавляем новый рест или обновляем существующий
        INSERT INTO rests (chat_id, user_id, administrator_user_id, assignment_date, valid_until)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (chat_id, user_id)
        DO UPDATE SET
            administrator_user_id = EXCLUDED.administrator_user_id,
            assignment_date = EXCLUDED.assignment_date,
            valid_until = EXCLUDED.valid_until;
        """, chat_id, user_id, administrator_user_id, now, valid_until
    )

async def remove_rest(chat_id: int, user_id: int):
    """Убираем рест пользователя в чате."""
    await db.execute(
        """
        DELETE FROM rests
        WHERE chat_id = $1
            AND user_id = $2;
        """, chat_id, user_id
    )

async def expire_rests() -> list[dict] | None:
    """Сбрасывает rest у всех пользователей, у которых дата истекла, и возвращает их список."""
    now = datetime.now(timezone.utc)

    # Обновляем всех сразу и возвращаем тех, у кого rest был сброшен
    rows = await db.fetchmany(
        """
        DELETE FROM rests
        WHERE valid_until <= $1
        RETURNING chat_id, user_id;
        """,
        now
    )

    # Преобразуем в список словарей
    return [{'chat_id': int(r['chat_id']), 'user_id': int(r['user_id'])} for r in rows] if rows else None

async def get_user_rest(chat_id: int, user_id: int) -> dict | None:
    """Возвращает информацию об ресте пользователя в чате по uid."""
    now = datetime.now(timezone.utc)
    rest = await db.fetchone(
        """
        SELECT administrator_user_id, assignment_date, valid_until
        FROM rests
        WHERE chat_id = $1
            AND user_id = $2
            AND valid_until > $3;
        """, chat_id, user_id, now
    )

    return {
        'administrator_user_id': int(rest['administrator_user_id']),
        'assignment_date': rest['assignment_date'],
        'valid_until': rest['valid_until'],
    } if rest else None
