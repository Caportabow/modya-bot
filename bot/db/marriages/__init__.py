import db
from asyncpg import Connection

async def make_marriage(chat_id: int, users: list[int]):
    """Создаём новый брак в чате между двумя пользователями."""
    
    if len(users) != 2:
        raise ValueError("Должно быть ровно 2 пользователя для создания брака.")
    
    await db.execute(
        """
        WITH new_marriage AS (
            INSERT INTO marriages (chat_id, date)
            VALUES ($1, NOW())
            RETURNING id
        )
        UPDATE users
        SET marriage_id = (SELECT id FROM new_marriage)
        WHERE chat_id = $1 AND user_id = ANY($2::bigint[]);
        """,
        chat_id, users
    )

async def get_marriages(chat_id: int, page: int, per_page: int = 10) -> dict | None:
    """
    Получаем все браки в чате с информацией:
    - points
    - date
    - список участников (id)
    Сортировка по points (по убыванию)
    """
    # Pagination
    limit = per_page + 1 # Берём на 1 больше, чтобы смотреть есть след. страница или нет
    offset = per_page * (page - 1)

    # Делаем join marriages и users, сортируем по points
    rows = await db.fetchmany(
        """
            SELECT m.id AS marriage_id, m.date, u.user_id AS user_id
            FROM marriages m
            JOIN users u ON u.marriage_id = m.id
            WHERE m.chat_id = $1
            ORDER BY m.date ASC
            LIMIT $2 OFFSET $3;
        """,
        chat_id, limit, offset
    )
    if rows:  # проверяем, что список не пуст
        if len(rows) == limit:
            rows = rows[:-1]  # убираем последний элемент, т.к он часть след. страницы
            next_page = page + 1
        else:
            next_page = None

    # Группируем участников по браку
    marriages = {}
    for row in rows:
        mid = row['marriage_id']
        if mid not in marriages:
            marriages[mid] = {
                "date": row['date'],
                "participants": []
            }
        marriages[mid]["participants"].append(int(row["user_id"]))

    return {
        "data": list(marriages.values()),
        "pagination": {
            "next_page": next_page,
            "prev_page": page-1 if page > 1 else None,
        }
    } if rows else None

async def get_user_marriage(chat_id: int, user_id: int):
    """
    Получаем информацию о браке пользователя:
    - date
    - список участников (id)
    """

    async with db.transaction() as conn:
        conn: Connection

        # Находим marriage_id пользователя
        row = await conn.fetchrow(
            """
                SELECT marriage_id
                FROM users
                WHERE chat_id = $1 AND user_id = $2
            """,
            chat_id, user_id
        )

        if not row or not row['marriage_id']:
            return None  # Пользователь не в браке

        marriage_id = row['marriage_id']

        # Получаем данные брака и участников
        rows = await conn.fetch(
            """
                SELECT m.date, u.user_id AS user_id
                FROM marriages m
                JOIN users u ON u.marriage_id = m.id
                WHERE m.id = $1
            """,
            marriage_id
        )

        children = await conn.fetch(
            """
                SELECT user_id 
                FROM users 
                WHERE chat_id = $1 AND parent_marriage_id = $2
            """, chat_id, marriage_id
        )

    if not rows:
        return None

    # Формируем ответ
    marriage_info = {
        "marriage_id": marriage_id,
        "date": rows[0]['date'],
        "participants": [int(r['user_id']) for r in rows],
        "children": [int(c['user_id']) for c in children] if children else None,
    }

    return marriage_info

async def delete_marriage(chat_id: int, marriage_id: int):
    async with db.transaction() as conn:
        conn: Connection
        # Удаляем брак
        await conn.execute(
            "DELETE FROM marriages WHERE id = $1 AND chat_id = $2",
            marriage_id, chat_id
        )

        # Обнуляем marriage_id, parent_marriage_id и adoption_date у всех связанных пользователей
        await conn.execute(
            """
                UPDATE users
                SET marriage_id = NULL,
                    parent_marriage_id = NULL,
                    adoption_date = NULL
                WHERE chat_id = $1 AND (marriage_id = $2 OR parent_marriage_id = $2)
            """,
            chat_id, marriage_id
        )
