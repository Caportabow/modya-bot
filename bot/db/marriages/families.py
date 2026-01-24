import os
from collections import defaultdict
from datetime import datetime, timezone

import db
from db.marriages import get_user_marriage

async def incest_cycle(chat_id: int, first_user_id: int, second_user_id: int) -> bool:
    """
        Проверяет, существует ли ЗАПРЕЩЁННАЯ вертикальная родственная связь
        между двумя пользователями в ЛЮБОМ направлении
        (предок ↔ потомок).

        Используется как предохранитель для СИММЕТРИЧНЫХ отношений
        (например: брак).

        Особенности:
        - Симметрична: порядок аргументов не имеет значения.
        - Возвращает True, если брак должен быть ЗАПРЕЩЁН.
        - Намеренно дублирует проверку в обе стороны
        для защиты от ошибок бизнес-логики.

        ❌ НЕ предназначена для усыновления.
        ❌ НЕ проверяет боковое родство (братья, тёти, кузены).
    """
    
    result = await db.fetchone(
        """
        WITH RECURSIVE family_tree AS (
            -- Начальная точка: находим родителей ОБОИХ пользователей
            SELECT 
                parent.user_id, 
                parent.parent_marriage_id,
                parent.marriage_id,
                child.user_id as child_id
            FROM users parent
            JOIN users child ON parent.marriage_id = child.parent_marriage_id
            WHERE child.user_id IN ($1, $2) AND child.chat_id = $3

            UNION ALL

            -- Рекурсивная часть: поднимаемся по дереву предков
            SELECT 
                grandparent.user_id, 
                grandparent.parent_marriage_id,
                grandparent.marriage_id,
                ft.child_id
            FROM users grandparent
            JOIN family_tree ft ON grandparent.marriage_id = ft.parent_marriage_id
            WHERE grandparent.chat_id = $3
        )
        -- Проверяем: есть ли первый пользователь среди предков второго ИЛИ наоборот
        SELECT 1 FROM family_tree 
        WHERE (child_id = $1 AND user_id = $2) 
           OR (child_id = $2 AND user_id = $1)
        LIMIT 1;
        """, 
        first_user_id, second_user_id, chat_id
    )
    
    return bool(result)

async def is_ancestor(chat_id: int, potential_ancestor_id: int, subject_id: int) -> bool:
    """
        Проверяет, является ли potential_ancestor_id предком subject_id
        (родитель, дед, прадед и т.д.).

        ⚠ ВАЖНО:
        - Функция НАПРАВЛЕННАЯ.
        - Порядок аргументов критичен.
        - Используется ТОЛЬКО там, где есть явные роли
        (например: усыновление / удочерение).

        ❌ НЕ ИСПОЛЬЗОВАТЬ для браков или других симметричных отношений.
        ❌ НЕ проверяет боковое родство (братья, тёти, кузены).
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

# TODO: исправить функцию чтобы в ДБ не был кусок фронтенда
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

    # Row example: 'parent_marriage_id': 6, 'parent_ids': [3, 6]
    os.makedirs("debug", exist_ok=True)
    with open("debug/database_result.py", "w", encoding="utf-8") as f:
        f.write(repr(rows))

    def make_id(person):
        """Возвращает уникальный id для человека: marriage_id если есть, иначе -user_id"""
        return person['marriage_id'] or -person['user_id']

    def make_processed_id(person):
        """Возвращает уникальный идентификатор для проверки дубликатов"""
        return f"{person['user_id']}:{person['parent_marriage_id']}"

    # 1. Группируем людей по их собственному marriage_id
    marriages = defaultdict(list)
    processed_marriages = set()  # используем set для O(1) проверки

    for person in rows:
        processed_id = make_processed_id(person)
        if processed_id in processed_marriages:
            continue

        marriages[make_id(person)].append(person)
        processed_marriages.add(processed_id)

    def get_children(marriage_id):
        """Ищет детей: это те браки, у которых parent_marriage_id равен текущему m_id"""
        children = set()
        processed_children = set()  # Отдельный список для детей

        for person in rows:
            if person['parent_marriage_id'] != marriage_id:
                continue

            processed_id = make_processed_id(person)
            if processed_id in processed_children:
                continue
            
            children.add(make_id(person))
            processed_children.add(processed_id)

        return children
    
    # 2. Находим корневые браки (у которых нет parent_marriage_id или он не найден в списке)
    # Вспомогательная функция для сборки узла брака
    def build_marriage_node(m_id, p_marriage_id_context):
        members = []
        for p in marriages[m_id]:
            # Если parent_marriage_id человека совпадает с контекстом этого узла, он "кровный"
            # Иначе он пришел из другой семьи (is_partner)
            is_partner = (
                p['parent_marriage_id'] != p_marriage_id_context
            ) or (
                p['parent_marriage_id'] is None
            )

            is_me = p['user_id'] == user_id
            
            members.append({
                'id': p['user_id'],
                'name': p['name'],
                'is_me': is_me,
                'is_partner': is_partner,
                'adoption_date': p['adoption_date']
            })

        if m_id < 0:  # Одиночка (использовали -user_id как ключ) (все айди браков положительные)
            return {
                'marriage_id': None,
                'parent_marriage_id': p_marriage_id_context,
                'members': members,
                'children': []
            }
        
        else: # Ищем детей
            children = get_children(m_id)
            
            # Рекурсивно собираем детей
            children_nodes = [build_marriage_node(child_id, m_id) for child_id in children]

            return {
                'marriage_id': m_id,
                'parent_marriage_id': p_marriage_id_context,
                'members': members,
                'children': children_nodes
            }

    # Находим стартовые точки (где parent_marriage_id None)
    root_ids = {p['marriage_id'] for p in rows if p['generation'] == -1}
    
    return [build_marriage_node(rid, None) for rid in root_ids]
