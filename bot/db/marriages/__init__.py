import db
from asyncpg import Connection


async def make_marriage(chat_id: int, users: list[int]) -> dict:
    """Создаём новый брак в чате между двумя пользователями."""
    
    if len(users) != 2:
        raise ValueError("Должно быть ровно 2 пользователя для создания брака.")
    
    async with db.transaction() as conn:
        conn: Connection
        # Проверяем, что оба пользователя не в браке
        existing = await conn.fetch(
            """
                SELECT user_id
                FROM users
                WHERE chat_id = $1
                AND user_id = ANY($2::bigint[])
                AND marriage_id IS NOT NULL;
            """,
            chat_id, users
        )
        
        if existing:
            in_marriage = [row['user_id'] for row in existing]
            return {"success": False, "in_marriage": in_marriage}
        
        # Создаём брак и обновляем пользователей одним запросом через CTE
        result = await conn.fetchrow(
            """
                WITH new_marriage AS (
                    INSERT INTO marriages (chat_id, date)
                    VALUES ($1, NOW())
                    RETURNING id
                )
                UPDATE users
                SET marriage_id = (SELECT id FROM new_marriage)
                WHERE chat_id = $1 AND user_id = ANY($2::bigint[])
                RETURNING marriage_id;
            """,
            chat_id, users
        )
        
        return {"success": True, "marriage_id": int(result['marriage_id'])} if result else {"success": False}

async def get_marriages(chat_id: int) -> list[dict]:
    """
    Получаем все браки в чате с информацией:
    - points
    - date
    - список участников (id)
    Сортировка по points (по убыванию)
    """

    # Делаем join marriages и users, сортируем по points
    rows = await db.fetchmany(
        """
            SELECT m.id AS marriage_id, m.date, u.user_id AS user_id
            FROM marriages m
            JOIN users u ON u.marriage_id = m.id
            WHERE m.chat_id = $1
            ORDER BY m.date ASC
        """,
        chat_id
    )

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

    return list(marriages.values())

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

async def are_in_same_marriage(chat_id: int, user1_id: int, user2_id: int) -> bool:
    """
    Проверяем, состоят ли два пользователя в одном браке в указанном чате.
    Возвращает True, если оба в браке и имеют одинаковый marriage_id.
    """

    rows = await db.fetchmany(
        """
            SELECT marriage_id
            FROM users
            WHERE chat_id = $1 AND user_id IN ($2, $3)
        """,
        chat_id, user1_id, user2_id
    )

    if len(rows) != 2:
        # Один или оба пользователя не найдены
        return False

    # Проверяем, что оба в браке и имеют одинаковый marriage_id
    marriage_ids = [r['marriage_id'] for r in rows]
    if None in marriage_ids or marriage_ids[0] != marriage_ids[1]:
        return False
        
    return marriage_ids[0]

async def delete_marriage(chat_id: int, user_id: int):
    async with db.transaction() as conn:
        conn: Connection

        # Получаем marriage_id, участников брака и детей в одном запросе
        marriage_data = await conn.fetchrow(
            """
                SELECT 
                    u.marriage_id,
                    ARRAY_AGG(DISTINCT u2.user_id) FILTER (WHERE u2.user_id IS NOT NULL) as participants,
                    ARRAY_AGG(DISTINCT children.user_id) FILTER (WHERE children.user_id IS NOT NULL) as children
                FROM users u
                LEFT JOIN users u2 ON u2.chat_id = u.chat_id AND u2.marriage_id = u.marriage_id
                LEFT JOIN users children ON children.chat_id = u.chat_id AND children.parent_marriage_id = u.marriage_id
                WHERE u.chat_id = $1 AND u.user_id = $2
                GROUP BY u.marriage_id
            """,
            chat_id, user_id
        )

        if not marriage_data or not marriage_data['marriage_id']:
            return False

        marriage_id = marriage_data['marriage_id']
        participant_ids = marriage_data['participants'] or []
        abandoned_child_ids = marriage_data['children'] or []

        # Удаляем брак
        await conn.execute(
            "DELETE FROM marriages WHERE id = $1 AND chat_id = $2",
            marriage_id, chat_id
        )

        # Обнуляем marriage_id и parent_marriage_id в одном запросе
        await conn.execute(
            """
                UPDATE users
                SET 
                    marriage_id = CASE WHEN marriage_id = $2 THEN NULL ELSE marriage_id END,
                    parent_marriage_id = CASE WHEN parent_marriage_id = $2 THEN NULL ELSE parent_marriage_id END,
                    adoption_date = CASE WHEN parent_marriage_id = $2 THEN NULL ELSE adoption_date END
                WHERE chat_id = $1 AND (marriage_id = $2 OR parent_marriage_id = $2)
            """,
            chat_id, marriage_id
        )

    partners = [int(pid) for pid in participant_ids if pid != user_id]
    
    return {
        "partner": partners[0] if partners else None,
        "abandoned_children": abandoned_child_ids,
    }
