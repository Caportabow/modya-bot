import aiosqlite
import asyncio
import json
import time
import io
from collections import Counter
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd

DB_PATH = "resources/stats.db"

with open("resources/russian_stopwords.json", "r", encoding="utf-8") as f:
    RUSSIAN_STOPWORDS = set(json.load(f))

db: aiosqlite.Connection
db_lock = asyncio.Lock()


async def init_db():
    global db
    db = await aiosqlite.connect(DB_PATH, timeout=15)
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")

    # Профиль пользователя в каждом чате
    await db.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        username TEXT,
        nickname TEXT,
        first_seen TIMESTAMP NOT NULL,
        last_update TIMESTAMP NOT NULL,
        PRIMARY KEY (chat_id, user_id)
    )
    """)

    # Сообщения
    await db.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        name TEXT,
        text TEXT,
        file_id TEXT NULL,
        date TIMESTAMP NOT NULL,
        PRIMARY KEY(chat_id, id)
    );
    """)

    # Цитаты
    await db.execute("""
    CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        sticker TEXT NOT NULL,
        UNIQUE(sticker)
    )
    """)

    await db.commit()


# --------------------
# Работа с пользователями
# --------------------

async def upsert_user(chat_id: int, uid: int, username: str | None, first_name: str):
    """Добавляем или обновляем пользователя в рамках конкретного чата."""
    now = int(time.time())

    global db
    async with db_lock:
        await db.execute(
            """
            INSERT INTO user_profiles(chat_id, user_id, username, nickname, first_seen, last_update)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                username=excluded.username,
                last_update=excluded.last_update
            """,
            (chat_id, uid, username, first_name, now, now)
        )
        await db.commit()

async def remove_user(chat_id: int, uid: int):
    """Удаляем профиль пользователя из чата."""
    global db
    async with db_lock:
        await db.execute("DELETE FROM user_profiles WHERE chat_id=? AND user_id=?", (chat_id, uid))
        await db.commit()

# Cтатистика
async def user_stats(chat_id: int, user_id: int):
    def format_timedelta(delta: timedelta) -> str:
        seconds = int(delta.total_seconds())
        if seconds <= 1:
            return "только что"
        elif seconds <= 60:
            return f"{seconds} сек."
        elif seconds <= 3600:
            return f"{seconds//60} мин."
        elif seconds <= 86400:
            return f"{seconds//3600} ч."
        else:
            return f"{delta.days} дн."
    now = int(time.time())
    one_day = now - 86400
    one_week = now - 7 * 86400
    one_month = now - 30 * 86400

    global db
    async with db_lock:
        cursor = await db.execute("""
            SELECT 
                MIN(m.date) AS first_seen,
                MAX(m.date) AS last_active,
                COUNT(m.id) AS total,
                SUM(CASE WHEN m.date >= ? THEN 1 ELSE 0 END) AS day_count,
                SUM(CASE WHEN m.date >= ? THEN 1 ELSE 0 END) AS week_count,
                SUM(CASE WHEN m.date >= ? THEN 1 ELSE 0 END) AS month_count
            FROM messages m
            WHERE m.chat_id = ? AND m.user_id = ?;
        """, (one_day, one_week, one_month, chat_id, user_id))
        row = await cursor.fetchone()

    if not row or row[0] is None:
        return None  # пользователь не найден / нет сообщений

    first_seen, last_active, total, day_count, week_count, month_count = row

    # преобразуем время в нормальный вид
    first_dt = datetime.fromtimestamp(first_seen)
    last_dt = datetime.fromtimestamp(last_active)
    age = datetime.now() - first_dt
    last_diff = datetime.now() - last_dt

    fav_word = await get_favorite_word(chat_id, user_id)

    return {
        "first_seen": f"{first_dt:%d.%m.%Y} ({(f'{age.days} д. ' if age.days > 0 else '')}{age.seconds//3600} ч.)",
        "last_active": format_timedelta(last_diff),
        "activity": f"{day_count} | {week_count} | {month_count} | {total}",
        "favorite_word": fav_word
    }

# Никнеймы
async def set_nickname(chat_id: int, uid: int, nickname: str | None):
    """Меняем кастомный ник пользователя в чате (или убираем)."""
    global db
    async with db_lock:
        await db.execute(
            "UPDATE user_profiles SET nickname=? WHERE chat_id=? AND user_id=?",
            (nickname, chat_id, uid)
        )
        await db.commit()

async def get_nickname(chat_id: int, uid: int | None = None, username: str | None = None) -> str | None:
    """Возвращает nickname пользователя в чате по uid или username (uid приоритетнее)."""
    if uid is None and username is None:
        raise ValueError("Нужно передать хотя бы uid или username")

    global db
    async with db_lock:
        if uid is not None:
            cursor = await db.execute(
                "SELECT nickname FROM user_profiles WHERE chat_id=? AND user_id=?",
                (chat_id, uid)
            )
        else:
            cursor = await db.execute(
                "SELECT nickname FROM user_profiles WHERE chat_id=? AND username=?",
                (chat_id, username)
            )

        row = await cursor.fetchone()
        return row[0] if row else None

# Хелперы для ТГ
async def get_uid(chat_id: int, username: str) -> int | None:
    """Возвращает user_id пользователя в чате по username."""
    global db
    async with db_lock:
        cursor = await db.execute(
            "SELECT user_id FROM user_profiles WHERE chat_id=? AND username=?",
            (chat_id, username)
        )

        row = await cursor.fetchone()
        return row[0] if row else None

# --------------------
# Работа с сообщениями
# --------------------

async def add_message(m_id:int, chat_id: int, user_id: int, name: str, text: str, date: int, file_id: str | None = None):
    """Добавляем сообщение пользователя в чате."""
    global db
    async with db_lock:
        await db.execute(
            "INSERT INTO messages (id, chat_id, user_id, name, text, file_id, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (m_id, chat_id, user_id, name, text, file_id, date)
        )
        await db.commit()

async def get_next_messages(chat_id: int, message_id: int, limit: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT user_id, name, text, file_id FROM messages
            WHERE chat_id = ? AND id > ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (chat_id, message_id, limit)
        )
        rows = await cursor.fetchall()
    return [{"user_id": r[0], "name": r[1], "text": r[2], "file_id": r[3]} for r in rows]

async def get_favorite_word(chat_id: int, user_id: int) -> dict | None:
    global db
    async with db_lock:
        # Сначала проверим, есть ли больше 50 сообщений
        async with db.execute(
            "SELECT COUNT(*) FROM messages WHERE chat_id=? AND user_id=? AND text IS NOT NULL AND TRIM(text) != ''",
            (chat_id, user_id)
        ) as cursor:
            count = (await cursor.fetchone())[0]
        if count <= 50:
            return None

        # Создаём счётчик
        word_counter = Counter()

        # Читаем сообщения потоково
        async with db.execute(
            "SELECT text FROM messages WHERE chat_id=? AND user_id=? AND text IS NOT NULL AND TRIM(text) != '' ORDER BY date LIMIT 150",
            (chat_id, user_id)
        ) as cursor:
            async for row in cursor:
                text = row[0]
                words = re.findall(r"\b\w+\b", text.lower())
                words = [w for w in words if w not in RUSSIAN_STOPWORDS]
                word_counter.update(words)

    if not word_counter:
        return None

    # Возвращаем самое частое слово
    return {
        "word": word_counter.most_common(1)[0][0],
        "count": word_counter.most_common(1)[0][1]
    }

# Подсчёт сообщений
async def plot_user_activity(chat_id: int, user_id: int):
    global db
    async with db_lock:
        cursor = await db.execute("""
            SELECT strftime('%Y-%m-%d', datetime(date, 'unixepoch')) AS day, COUNT(*) AS count
            FROM messages
            WHERE chat_id = ? AND user_id = ?
            GROUP BY day
            ORDER BY day
        """, (chat_id, user_id))
        rows = await cursor.fetchall()

    if not rows:
        return None

    # Конвертируем в DataFrame
    df = pd.DataFrame(rows, columns=["date", "count"])
    df["date"] = pd.to_datetime(df["date"])  # оставляем datetime для корректного порядка

    # Заполняем пропущенные дни нулями
    df = df.set_index("date").asfreq("D", fill_value=0).reset_index()

    # Создаём подписи для оси X
    df["date_str"] = df["date"].dt.strftime("%d.%m")

    # Рисуем график
    plt.figure(figsize=(10, 5))
    plt.bar(df["date_str"], df["count"], color="#1d74e6")
    plt.title("Статистика активности", fontsize=12)
    plt.ylabel("Кол-во сообщений")
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)

    return buffer.getvalue()

async def count_messages(chat_id: int, user_id: int, since: int | None = None):
    """Считаем количество сообщений пользователя в чате (если since=None → за всё время)."""
    global db
    async with db_lock:
        if since is not None:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM messages WHERE chat_id=? AND user_id=? AND date>=?",
                (chat_id, user_id, since)
            )
        else:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM messages WHERE chat_id=? AND user_id=?",
                (chat_id, user_id)
            )
        row = await cursor.fetchone()
        return row[0] if row else 0
    
async def top_users(chat_id: int, limit: int = 10, since: int | None = None):
    """
    Возвращает топ пользователей в чате по количеству сообщений.
    :param chat_id: ID чата
    :param limit: сколько пользователей вернуть
    :param since: если указано, считать только сообщения после этой метки времени
    :return: список (user_id, nickname, count)
    """
    global db
    async with db_lock:
        if since is not None:
            cursor = await db.execute("""
                SELECT u.user_id, u.nickname, COUNT(m.id) as msg_count
                FROM user_profiles u
                LEFT JOIN messages m ON u.chat_id = m.chat_id AND u.user_id = m.user_id AND m.date >= ?
                WHERE u.chat_id = ?
                GROUP BY u.user_id
                ORDER BY msg_count DESC
                LIMIT ?
            """, (since, chat_id, limit))
        else:
            cursor = await db.execute("""
                SELECT u.user_id, u.nickname, COUNT(m.id) as msg_count
                FROM user_profiles u
                LEFT JOIN messages m ON u.chat_id = m.chat_id AND u.user_id = m.user_id
                WHERE u.chat_id = ?
                GROUP BY u.user_id
                ORDER BY msg_count DESC
                LIMIT ?
            """, (chat_id, limit))

        rows = await cursor.fetchall()
        return [{"user_id": row[0], "nickname": row[1], "count": row[2]} for row in rows]

# --------------------
# Работа с цитатами
# --------------------

async def add_quote(chat_id: int, sticker_id: str):
    """Добавляем цитату (стикер) пользователя в чате."""
    global db
    async with db_lock:
        await db.execute(
            """
            INSERT INTO quotes (chat_id, sticker)
            VALUES (?, ?)
            ON CONFLICT(sticker) DO NOTHING
            """,
            (chat_id, sticker_id)
        )

        await db.commit()

async def get_random_quote(chat_id: int) -> str | None:
    """Возвращает случайную цитату (стикер) в чате."""
    global db
    async with db_lock:
        cursor = await db.execute(
            "SELECT sticker FROM quotes WHERE chat_id=? ORDER BY RANDOM() LIMIT 1",
            (chat_id,)  # <-- добавляем запятую
        )
        row = await cursor.fetchone()
        return row[0] if row else None
    