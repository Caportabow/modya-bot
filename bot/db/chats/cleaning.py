import db
from datetime import datetime, timezone, timedelta

async def fetch_chats_for_scheduled_cleaning() -> list[int]:
    """
    Получаем список чатов, в которых пришло время провести чистку,
    с учётом дня недели и времени.
    """
    rows = await db.fetchmany(
        """
        SELECT chat_id
        FROM chats
        WHERE autoclean_enabled = true
            AND cleaning_day_of_week = EXTRACT(ISODOW FROM CURRENT_DATE)
            AND cleaning_time <= CURRENT_TIME
            AND (
                last_auto_cleaning_at IS NULL
                OR last_auto_cleaning_at::date < CURRENT_DATE
            );
        """
    )
    return [row["chat_id"] for row in rows]

async def update_last_cleaning_time(chat_id: int):
    await db.execute(
        """
        UPDATE chats
        SET last_auto_cleaning_at = NOW()
        WHERE chat_id = $1;
        """, chat_id
    )

async def check_cleanability(chat_id: int) -> bool:
    ability = await db.fetchval(
        """
        SELECT EXISTS (
            SELECT 1
            FROM chats
            WHERE chat_id = $1
            AND cleaning_lookback IS NOT NULL
            AND cleaning_eligibility_duration IS NOT NULL
            AND cleaning_min_messages IS NOT NULL
            AND cleaning_max_inactive IS NOT NULL
        );
        """, chat_id
    )

    return bool(ability)

async def check_cleaning_accuracy(chat_id: int) -> bool:
    """
    Проверяет корректность возможного проведения чистки в чате.
    Возвращает True если чистку уже можно провести, иначе False.
    """
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    query = """
    SELECT
        CASE
            WHEN MIN(date) <= $1 THEN TRUE
            ELSE FALSE
        END AS week_passed
    FROM messages
    WHERE chat_id = $2;
    """
    cleaning_possibility = await db.case(query, week_ago, chat_id)

    return cleaning_possibility

async def minmsg_users(chat_id: int, min_messages: int, page: int, per_page: int = 20):
    """Возвращает список пользователей, у которых сообщений меньше, чем требуется."""
    cleaning_data = await db.fetchone(
        """
        SELECT
            cleaning_lookback,
            cleaning_eligibility_duration
        FROM chats
            WHERE chat_id = $1;
        """,
        chat_id
    )
    if not cleaning_data:
        raise ValueError("Чат не найден")

    now_dt = datetime.now(timezone.utc)
    cutoff_date = now_dt - cleaning_data["cleaning_lookback"]
    min_activity_age = now_dt - cleaning_data["cleaning_eligibility_duration"]

    # Pagination
    limit = per_page + 1 # Берём на 1 больше, чтобы смотреть есть след. страница или нет
    offset = per_page * (page - 1)

    query = """
        WITH first_message_dates AS (
            SELECT 
                chat_id, 
                sender_user_id,
                MIN(date) AS first_message_date
            FROM messages
            WHERE chat_id = $2
            GROUP BY chat_id, sender_user_id
        )
        SELECT 
            u.user_id AS sender_user_id,
            COUNT(m.message_id) AS message_count
        FROM users u
        LEFT JOIN messages m
            ON m.sender_user_id = u.user_id
            AND m.chat_id = u.chat_id
            AND m.date >= $3
        LEFT JOIN first_message_dates fmd
            ON fmd.chat_id = u.chat_id
            AND fmd.sender_user_id = u.user_id
        LEFT JOIN rests r
            ON r.chat_id = u.chat_id
            AND r.user_id = u.user_id
            AND r.valid_until >= $1   -- Только активные ресты
        WHERE u.chat_id = $2
        AND r.user_id IS NULL        -- Пользователи без активного рестa
        AND (
                fmd.first_message_date IS NULL
                OR fmd.first_message_date <= $4
            )
        GROUP BY u.user_id
        HAVING COUNT(m.message_id) < $5
        ORDER BY message_count DESC
        LIMIT $6 OFFSET $7;
    """

    rows = await db.fetchmany(
        query,
        now_dt,
        chat_id,
        cutoff_date,
        min_activity_age,
        min_messages,
        limit,
        offset
    )
    if rows:  # проверяем, что список не пуст
        if len(rows) == limit:
            rows = rows[:-1]  # убираем последний элемент, т.к он часть след. страницы
            next_page = page + 1
        else:
            next_page = None

    data = {
        "data": [{
            "user_id": int(row["sender_user_id"]),
            "count": int(row["message_count"])
        } for row in rows],
        "pagination": {
            "next_page": next_page,
            "prev_page": page-1 if page > 1 else None,
        }
    } if rows else None
    
    return data

async def inactive_users(chat_id: int, duration: timedelta, page: int, per_page: int = 20):
    """
    Возвращает пользователей, которые есть в таблице users,
    раньше писали сообщения, но не писали за указанный период.
    Для каждого пользователя указывается дата его последнего сообщения.
    """
    now_dt = datetime.now(timezone.utc)
    since = now_dt - duration

    # Pagination
    limit = per_page + 1 # Берём на 1 больше, чтобы смотреть есть след. страница или нет
    offset = per_page * (page - 1)

    query = """
        SELECT 
            u.user_id,
            MAX(m.date) AS last_message_date
        FROM users u
        LEFT JOIN messages m
            ON m.chat_id = u.chat_id
            AND m.sender_user_id = u.user_id
        LEFT JOIN rests r
            ON r.chat_id = u.chat_id
            AND r.user_id = u.user_id
            AND r.valid_until >= $2  -- активные ресты
        WHERE 
            u.chat_id = $1
            AND r.user_id IS NULL      -- только пользователи без активного рестa
        GROUP BY u.user_id
        HAVING 
            COALESCE(MAX(m.date), '1970-01-01') < $3
        ORDER BY last_message_date ASC
        LIMIT $4 OFFSET $5;
    """

    rows = await db.fetchmany(query, chat_id, now_dt, since, limit, offset)
    if rows:  # проверяем, что список не пуст
        if len(rows) == limit:
            rows = rows[:-1]  # убираем последний элемент, т.к он часть след. страницы
            next_page = page + 1
        else:
            next_page = None

    data = {
        "data": [{
            "user_id": int(row["user_id"]),
            "last_message_date": row["last_message_date"]
        } for row in rows],
        "pagination": {
            "next_page": next_page,
            "prev_page": page-1 if page > 1 else None,
        }
    } if rows else None

    return data

async def do_cleaning(chat_id: int, page: int, per_page: int = 20):
    """
    Проводит чистку чата.
    Возвращает список пользователей, которые подлежат исключению, объединяя критерии:
    1. Мало сообщений за период cleaning_lookback (minmsg_users).
    2. Полное отсутствие активности дольше cleaning_max_inactive (inactive_users).
    При этом учитывается "иммунитет" для новичков (eligibility_duration) и активные ресты.
    """

    # Pagination
    limit = per_page + 1 # Берём на 1 больше, чтобы смотреть есть след. страница или нет
    offset = per_page * (page - 1)
    
    # 1. Получаем настройки чата
    cleaning_data = await db.fetchone(
        """
        SELECT
            cleaning_lookback,
            cleaning_eligibility_duration,
            cleaning_min_messages,
            cleaning_max_inactive
        FROM chats
        WHERE chat_id = $1
            AND cleaning_min_messages IS NOT NULL
            AND cleaning_max_inactive IS NOT NULL;
        """,
        chat_id
    )
    if not cleaning_data:
        raise ValueError("Чат не найден")

    # 2. Рассчитываем временные метки
    now_dt = datetime.now(timezone.utc)
    lookback_cutoff = now_dt - cleaning_data["cleaning_lookback"]    
    eligibility_cutoff = now_dt - cleaning_data["cleaning_eligibility_duration"]    
    inactive_cutoff = now_dt - cleaning_data["cleaning_max_inactive"]
    min_messages = cleaning_data["cleaning_min_messages"]

    # 3. Единый запрос
    query = """
        SELECT 
            u.user_id,
            -- Считаем сообщения только внутри окна lookback
            COUNT(CASE WHEN m.date >= $3 THEN 1 END) AS recent_message_count,
            -- Находим дату самого последнего сообщения вообще
            MAX(m.date) AS last_message_date,
            -- Находим дату самого первого сообщения (для проверки "новичек или нет")
            MIN(m.date) AS first_message_date
        FROM users u
        LEFT JOIN messages m
            ON m.sender_user_id = u.user_id
            AND m.chat_id = u.chat_id
        LEFT JOIN rests r
            ON r.chat_id = u.chat_id
            AND r.user_id = u.user_id
            AND r.valid_until >= $2  -- Проверяем активные ресты
        WHERE 
            u.chat_id = $1
            AND r.user_id IS NULL    -- Исключаем тех, у кого активный рест
        GROUP BY u.user_id
        HAVING 
            -- Условие 1: Пользователь уже "созрел" для чистки (прошел испытательный срок)
            (MIN(m.date) IS NULL OR MIN(m.date) <= $4)
            AND (
                -- Условие 2 (OR): Либо мало сообщений за последнее время
                COUNT(CASE WHEN m.date >= $3 THEN 1 END) < $5
                OR
                -- Либо последнее сообщение было слишком давно (или никогда)
                COALESCE(MAX(m.date), '1970-01-01'::timestamptz) < $6
            )
        ORDER BY recent_message_count ASC
        LIMIT $7 OFFSET $8;
    """

    rows = await db.fetchmany(
        query,
        chat_id,            # $1
        now_dt,             # $2
        lookback_cutoff,    # $3
        eligibility_cutoff, # $4
        min_messages,       # $5
        inactive_cutoff,    # $6
        limit,              # $7
        offset,             # $8
    )
    if rows:  # проверяем, что список не пуст
        if len(rows) == limit:
            rows = rows[:-1]  # убираем последний элемент, т.к он часть след. страницы
            next_page = page + 1
        else:
            next_page = None

    # 4. Формируем результат
    result = {
        "users": [],
        "data": {
            "inactive_cutoff": cleaning_data["cleaning_max_inactive"],
            "min_messages": min_messages,
            "сleaning_lookback": cleaning_data["cleaning_lookback"],
            "pagination": {
                "next_page": next_page,
                "prev_page": page-1 if page > 1 else None,
            }
        }
    }

    if rows:
        for row in rows:
            result["users"].append({
                "user_id": int(row["user_id"]),
                "message_count": int(row["recent_message_count"]),
                "last_message": now_dt - row["last_message_date"] if row["last_message_date"] else None
            })

    return result
