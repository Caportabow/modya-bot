from datetime import datetime, timezone
from utils.time import format_timedelta

import db
from . import get_user_marriage

async def is_ancestor(chat_id: int, potential_ancestor_id: int, subject_id: int) -> bool:
    """
    Проверяет, является ли potential_ancestor_id предком для subject_id.
    """

    # Аргументы: $1 = subject_id (кто усыновляет), $2 = chat_id, $3 = potential_ancestor_id (кого проверяем)
    result = await db.fetchone(
        """
        WITH RECURSIVE family_tree AS (
            -- 1. Начальная точка: находим родителей subject_id (того, кто усыновляет)
            -- Мы ищем людей, чей marriage_id совпадает с parent_marriage_id нашего субъекта
            SELECT 
                parent.user_id, 
                parent.parent_marriage_id,
                parent.marriage_id
            FROM users parent
            JOIN users child ON parent.marriage_id = child.parent_marriage_id
            WHERE child.user_id = $1 AND child.chat_id = $2

            UNION ALL

            -- 2. Рекурсивная часть: ищем родителей найденных людей (дедушек, прадедушек...)
            SELECT 
                grandparent.user_id, 
                grandparent.parent_marriage_id,
                grandparent.marriage_id
            FROM users grandparent
            JOIN family_tree child ON grandparent.marriage_id = child.parent_marriage_id
            WHERE grandparent.chat_id = $2
        )
        -- 3. Финал: проверяем, есть ли искомый "ребенок" в этом списке предков
        SELECT 1 FROM family_tree WHERE user_id = $3 LIMIT 1;
        """, subject_id, chat_id, potential_ancestor_id
    )

    return bool(result)

async def is_parent(chat_id: int, parent_id: int, child_id: int) -> bool:
    """
    Проверяет, является ли parent_id родителем для child_id.
    """
    row = await db.fetchone(
        """
        SELECT 1
        FROM users
        WHERE chat_id = $1 AND user_id = $2 AND parent_marriage_id = (
            SELECT marriage_id
            FROM users
            WHERE chat_id = $1 AND user_id = $3
        )
        """,
        chat_id, child_id, parent_id
    )
    return bool(row)

async def is_child(chat_id: int, user_id: int) -> bool:
    """
    Проверяет, есть ли у пользователя родители.
    """
    row = await db.fetchone(
        """
        SELECT 1
        FROM users
        WHERE chat_id = $1 AND user_id = $2 AND parent_marriage_id IS NOT NULL
        """,
        chat_id, user_id
    )
    return bool(row)

async def check_adoption_possibility(chat_id: int, child_id: int, marriage: dict | None = None, parent_id: int | None = None) -> dict:
    """
    Проверяет, может ли пользователь усыновить другого пользователя.
    Возвращает True, если усыновление возможно, иначе False.
    """
    # 0. Получаем брак, если не передан
    if not marriage:
        marriage = await get_user_marriage(chat_id, parent_id)
        if not marriage:
            return {"success": False, "error": "Вам нужен супруг, чтобы завести детей."}
    
    # 1. Проверяем, не является ли ребенок уже чьим-то ребенком
    child_row = await db.fetchone(
        "SELECT parent_marriage_id FROM users WHERE chat_id = $1 AND user_id = $2",
        chat_id, child_id
    )
    if child_row and child_row['parent_marriage_id']:
        return {"success": False, "error": "Этот пользователь уже чей-то ребёнок."}

    # 2. Проверяем, не является ли ребенок одним из супругов в этом браке
    if child_id in marriage['participants']:
        return {"success": False, "error": "Вы не можете стать родителем для своего супруга."}
    
    # 3. Проверяем, не является ли ребенок уже ребенком этой пары
    for spouse in marriage['participants']:
        ancestor = await is_ancestor(chat_id, child_id, spouse)
        if ancestor:
            return {"success": False, "error": "Вы не можете стать родителем своего предка."}

    return {"success": True}  # Усыновление возможно

async def adopt_child(chat_id: int, parent_id: int, child_id: int) -> dict:
    """
    Позволяет паре в браке усыновить другого пользователя.
    """
    # Проверяем, что 'родитель' состоит в браке
    parent_marriage = await get_user_marriage(chat_id, parent_id)
    if not parent_marriage:
        return {"success": False, "error": "Вы должны быть в браке, чтобы усыновлять детей."}

    marriage_id = parent_marriage['marriage_id']

    # Записываем ребенка в семью
    await db.execute(
        """
        UPDATE users 
        SET parent_marriage_id = $1, adoption_date = $2
        WHERE chat_id = $3 AND user_id = $4
        """,
        marriage_id, datetime.now(timezone.utc), chat_id, child_id
    )

    return {"success": True}

async def abandon(chat_id: int, child_id: int):
    """
    Убираем ребенка из семьи.
    """
    await db.execute(
        """
        UPDATE users 
        SET parent_marriage_id = NULL, adoption_date = NULL
        WHERE chat_id = $1 AND user_id = $2
        """,
        chat_id, child_id
    )
    
async def get_family_tree_data(chat_id: int, user_id: int) -> list | None:
    query = """
        WITH RECURSIVE 
        marriage_parents AS (
            -- Собираем ВСЕ parent_marriage_id для каждого брака
            SELECT 
                marriage_id,
                ARRAY_AGG(DISTINCT parent_marriage_id) FILTER (WHERE parent_marriage_id IS NOT NULL) as parent_ids
            FROM users
            WHERE chat_id = $1 AND marriage_id IS NOT NULL
            GROUP BY marriage_id
        ),
        
        family_tree AS (
            -- ЯКОРЬ (не рекурсивная часть)
            SELECT 
                u.user_id,
                u.marriage_id,
                u.parent_marriage_id,
                COALESCE(mp.parent_ids, '{}') as parent_ids,
                0 AS generation,
                ARRAY[u.user_id] AS visited_users
            FROM users u
            LEFT JOIN marriage_parents mp ON u.marriage_id = mp.marriage_id
            WHERE u.chat_id = $1 AND u.user_id = $2

            UNION ALL

            -- РЕКУРСИЯ (рекурсивная часть)
            SELECT 
                u.user_id,
                u.marriage_id,
                u.parent_marriage_id,
                COALESCE(mp.parent_ids, '{}') as parent_ids,
                CASE 
                    WHEN (COALESCE(mp.parent_ids, '{}') && ARRAY[ft.marriage_id]) OR (u.parent_marriage_id = ft.marriage_id)
                    THEN ft.generation + 1
                    WHEN (ft.parent_ids && ARRAY[u.marriage_id]) OR (u.marriage_id = ft.parent_marriage_id)
                    THEN ft.generation - 1
                END AS generation,
                ft.visited_users || u.user_id
            FROM users u
            LEFT JOIN marriage_parents mp ON u.marriage_id = mp.marriage_id
            JOIN family_tree ft ON (
                -- Вниз: дети текущего брака
                (
                    (COALESCE(mp.parent_ids, '{}') && ARRAY[ft.marriage_id] OR u.parent_marriage_id = ft.marriage_id)
                    AND ft.generation < 2
                )
                OR
                -- Вверх: родители текущего человека
                (
                    (ft.parent_ids && ARRAY[u.marriage_id] OR u.marriage_id = ft.parent_marriage_id)
                    AND ft.parent_marriage_id IS NOT NULL 
                    AND ft.generation > -2
                )
            )
            WHERE u.chat_id = $1
            AND ft.generation BETWEEN -2 AND 2
            AND NOT (u.user_id = ANY(ft.visited_users))
        ),

        siblings AS (
            SELECT
                s.user_id,
                s.marriage_id,
                s.parent_marriage_id,
                COALESCE(mp.parent_ids, '{}') as parent_ids,
                0 AS generation
            FROM users s
            LEFT JOIN marriage_parents mp ON s.marriage_id = mp.marriage_id
            JOIN family_tree ft ON ft.generation = -1
                AND s.parent_marriage_id = ft.marriage_id
            WHERE s.chat_id = $1 
            AND s.user_id <> $2
        ),

        extended AS (
            SELECT user_id, marriage_id, parent_marriage_id, parent_ids, generation 
            FROM family_tree
            UNION 
            SELECT user_id, marriage_id, parent_marriage_id, parent_ids, generation 
            FROM siblings
        )

        SELECT 
            et.user_id,
            et.marriage_id,
            et.parent_marriage_id,
            et.parent_ids,
            et.generation,
            u.nickname AS name,
            u.adoption_date,
            spouse.user_id AS spouse_id,
            spouse.nickname AS spouse_name
        FROM extended et
        LEFT JOIN users u 
            ON u.user_id = et.user_id AND u.chat_id = $1
        LEFT JOIN users spouse 
            ON spouse.marriage_id = et.marriage_id
            AND spouse.user_id <> et.user_id
            AND spouse.chat_id = $1
        ORDER BY et.generation, et.user_id;
    """
    
    rows = await db.fetchmany(query, chat_id, user_id)
    if not rows:
        return None

    nodes = {}
    person_to_node = {}
    
    def resolve_node_key(marriage_id: int | None, user_id: int):
        if marriage_id:
            return marriage_id
        return -user_id

    now = datetime.now(timezone.utc)

    # === 1. Создаём узлы и заполняем участников ===
    for row in rows:
        node_key = resolve_node_key(row["marriage_id"], row["user_id"])

        if node_key not in nodes:
            nodes[node_key] = {
                "marriage_id": row["marriage_id"],
                "parent_marriage_id": row["parent_marriage_id"],
                "parent_ids": row["parent_ids"] if row["parent_ids"] else [],
                "members": [],
                "children": []
            }

        node = nodes[node_key]

        if not any(m["id"] == row["user_id"] for m in node["members"]):
            adoption_display = (
                f"сын/дочь уже {format_timedelta(now - row["adoption_date"], adder=False)}"
                if row["adoption_date"] 
                else "пока без родителей"
            )
            
            node["members"].append({
                "id": row["user_id"],
                "name": row["name"] or str(row["user_id"]),
                "adoption_date": adoption_display,
                "is_me": (row["user_id"] == user_id)
            })

        person_to_node[row["user_id"]] = node_key

    # === 2. Добавляем супругов ===
    for row in rows:
        node_key = resolve_node_key(row["marriage_id"], row["user_id"])
        node = nodes[node_key]

        if row["spouse_id"] and row["spouse_id"] not in person_to_node:
            adoption_display = (
                f"сын/дочь уже {format_timedelta(now - row["adoption_date"], adder=False)}"
                if row["adoption_date"] 
                else "пока без родителей"
            )
            
            node["members"].append({
                "id": row["spouse_id"],
                "name": row["spouse_name"] or str(row["spouse_id"]),
                "adoption_date": adoption_display,
                "is_me": False
            })
            person_to_node[row["spouse_id"]] = node_key

    # === 3. Связываем узлы в дерево ===
    roots = []
    
    for node_key, node in nodes.items():
        parent_ids = node.get("parent_ids", [])
        parent_marriage_id = node.get("parent_marriage_id")
        
        # Для браков с множественными родителями
        if parent_ids:
            for parent_id in parent_ids:
                if parent_id in nodes:
                    nodes[parent_id]["children"].append(node)
        # Для одиночек с одним родителем
        elif parent_marriage_id and parent_marriage_id in nodes:
            nodes[parent_marriage_id]["children"].append(node)
        else:
            roots.append(node)

    if len(roots) == 1 and len(roots[0]["members"]) == 1 and not roots[0]["children"]:
        return None

    return roots
