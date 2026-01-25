import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

import asyncpg
from asyncpg import Pool

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Глобальный пул соединений
pool: Optional[Pool] = None


async def init_db() -> None:
    """
    Инициализирует пул соединений с базой данных.

    Создаёт пул соединений с параметрами из конфигурации
    и создаёт необходимые таблицы, если они не существуют.
    """
    global pool
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=5,
        command_timeout=100  # Таймаут для долгих запросов
    )
    logger.info("✅ Pool соединений с БД создан")

    # Создаём таблицы, если их нет
    async with pool.acquire() as conn:
        await _create_tables(conn)
        logger.info("📦 Таблицы проверены/созданы")


async def close_db() -> None:
    """
    Закрывает пул соединений с базой данных.

    Вызывается при завершении работы приложения.
    """
    global pool
    if pool is not None:
        await pool.close()
        logger.info("🔒 Пул соединений с БД закрыт")


@asynccontextmanager
async def connection():
    """
    Асинхронный контекстный менеджер для безопасного доступа к БД.

    Yields:
        Соединение с базой данных.

    Raises:
        RuntimeError: Если пул соединений не инициализирован.
    """
    if pool is None:
        raise RuntimeError(
            "Пул соединений с БД не инициализирован. "
            "Вызовите init_db() сначала."
        )
    async with pool.acquire() as conn:
        yield conn


async def fetchmany(query: str, *args: Any) -> list[dict]:
    """
    Выполняет SELECT-запрос и возвращает все записи.

    Args:
        query: SQL-запрос.
        *args: Параметры для запроса.

    Returns:
        Список словарей с результатами запроса.
    """
    async with connection() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]


async def fetchone(query: str, *args: Any) -> Optional[dict]:
    """
    Выполняет SELECT-запрос и возвращает одну запись.

    Args:
        query: SQL-запрос.
        *args: Параметры для запроса.

    Returns:
        Словарь с записью или None, если запись не найдена.
    """
    async with connection() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetchval(query: str, *args: Any) -> Any:
    """
    Выполняет запрос и возвращает одно значение.

    Args:
        query: SQL-запрос.
        *args: Параметры для запроса.

    Returns:
        Значение первого столбца первой строки или None.
    """
    async with connection() as conn:
        val = await conn.fetchval(query, *args)
        return val or None


async def case(query: str, *args: Any) -> bool:
    """
    Выполняет CASE-запрос и возвращает булево значение.

    Args:
        query: SQL-запрос с CASE.
        *args: Параметры для запроса.

    Returns:
        True если запрос вернул результат, иначе False.
    """
    async with connection() as conn:
        val = await conn.fetchval(query, *args)
        return bool(val)


async def count(query: str, *args: Any) -> int:
    """
    Выполняет COUNT-запрос и возвращает количество.

    Args:
        query: SQL-запрос с COUNT.
        *args: Параметры для запроса.

    Returns:
        Количество записей.
    """
    async with connection() as conn:
        val = await conn.fetchval(query, *args)
        return val or 0


@asynccontextmanager
async def transaction():
    """
    Асинхронный контекстный менеджер для транзакции.

    Yields:
        Соединение с активной транзакцией.
    """
    async with connection() as conn:
        async with conn.transaction():
            yield conn


async def execute(query: str, *args: Any) -> str:
    """
    Выполняет INSERT/UPDATE/DELETE без возврата данных.

    Args:
        query: SQL-запрос.
        *args: Параметры для запроса.

    Returns:
        Результат выполнения запроса.
    """
    async with connection() as conn:
        return await conn.execute(query, *args)


async def _create_tables(conn: asyncpg.Connection) -> None:
    """
    Создаёт необходимые таблицы, если их ещё нет.

    Args:
        conn: Соединение с базой данных.
    """
    # Чаты
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id BIGINT PRIMARY KEY,

            max_warns INT NOT NULL DEFAULT 3 CHECK (max_warns BETWEEN 1 AND 100),

            -- Настройки чистки
            cleaning_min_messages INT DEFAULT NULL,
            cleaning_max_inactive INTERVAL DEFAULT NULL,

            -- Расширенные настройки чистки
            cleaning_eligibility_duration INTERVAL NOT NULL DEFAULT '4 days',
            cleaning_lookback INTERVAL NOT NULL DEFAULT '7 days',

            -- Автоочистка
            autoclean_enabled BOOLEAN NOT NULL DEFAULT false,
            cleaning_time TIME DEFAULT '00:00',
            cleaning_day_of_week SMALLINT DEFAULT 7,
            last_auto_cleaning_at TIMESTAMPTZ DEFAULT NULL
        );
    """)

    # Браки
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS marriages (
            id BIGSERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            date TIMESTAMPTZ NOT NULL,

            -- Связи
            CONSTRAINT marriages_chat_fk
                FOREIGN KEY (chat_id)
                REFERENCES chats(chat_id)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_marriages_chat
            ON marriages(chat_id);
    """)

    # Пользователи
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            username TEXT DEFAULT NULL,
            nickname TEXT NOT NULL,
            marriage_id BIGINT DEFAULT NULL,
            parent_marriage_id BIGINT DEFAULT NULL,
            adoption_date TIMESTAMPTZ DEFAULT NULL,
            PRIMARY KEY (chat_id, user_id),

            -- Связи
            CONSTRAINT users_chat_fk
                FOREIGN KEY (chat_id)
                REFERENCES chats(chat_id)
                ON DELETE CASCADE
                ON UPDATE CASCADE,

            CONSTRAINT users_marriage_fk
                FOREIGN KEY (marriage_id)
                REFERENCES marriages(id)
                ON DELETE SET NULL,

            CONSTRAINT users_parent_marriage_fk
                FOREIGN KEY (parent_marriage_id)
                REFERENCES marriages(id)
                ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_users_marriage
            ON users(marriage_id);

        CREATE INDEX IF NOT EXISTS idx_users_parent_marriage
            ON users(parent_marriage_id);
    """)

    # Сообщения
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id BIGINT NOT NULL,
            chat_id BIGINT NOT NULL,
            sender_user_id BIGINT NOT NULL,
            date TIMESTAMPTZ NOT NULL,
            forward_user_id BIGINT NULL,
            name TEXT NOT NULL,
            text TEXT NULL,
            file_id TEXT NULL,
            PRIMARY KEY (message_id, chat_id),

            -- Связи
            CONSTRAINT messages_chat_fk
                FOREIGN KEY (chat_id)
                REFERENCES chats(chat_id)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_messages_with_text
            ON messages(chat_id, sender_user_id, date DESC)
            WHERE text IS NOT NULL AND text != '';

        CREATE INDEX IF NOT EXISTS idx_messages_date
            ON messages(date DESC);
    """)

    # Цитаты
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id BIGSERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            sticker_file_id TEXT NOT NULL,
            UNIQUE(chat_id, sticker_file_id),

            -- Связи
            CONSTRAINT quotes_chat_fk
                FOREIGN KEY (chat_id)
                REFERENCES chats(chat_id)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        );
    """)

    # Варны
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id BIGSERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            administrator_user_id BIGINT NOT NULL,
            assignment_date TIMESTAMPTZ NOT NULL,
            reason TEXT NULL,
            expire_date TIMESTAMPTZ DEFAULT NULL,

            -- Связи
            CONSTRAINT warnings_chat_fk
                FOREIGN KEY (chat_id)
                REFERENCES chats(chat_id)
                ON DELETE CASCADE
                ON UPDATE CASCADE,

            CONSTRAINT warnings_user_fk
                FOREIGN KEY (chat_id, user_id)
                REFERENCES users(chat_id, user_id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_user_warnings
            ON warnings(chat_id, user_id);

        CREATE INDEX IF NOT EXISTS idx_warnings_with_expire_date
            ON warnings(expire_date)
            WHERE expire_date IS NOT NULL;
    """)

    # Награды
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS awards (
            id BIGSERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            giver_user_id BIGINT NOT NULL,
            assignment_date TIMESTAMPTZ NOT NULL,
            award TEXT NOT NULL,

            -- Связи
            CONSTRAINT awards_chat_fk
                FOREIGN KEY (chat_id)
                REFERENCES chats(chat_id)
                ON DELETE CASCADE
                ON UPDATE CASCADE,

            CONSTRAINT awards_user_fk
                FOREIGN KEY (chat_id, user_id)
                REFERENCES users(chat_id, user_id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_user_awards
            ON awards(chat_id, user_id);
    """)

    # Ресты
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS rests (
            chat_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            administrator_user_id BIGINT NOT NULL,
            assignment_date TIMESTAMPTZ NOT NULL,
            valid_until TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (chat_id, user_id),

            -- Связи
            CONSTRAINT rests_chat_fk
                FOREIGN KEY (chat_id)
                REFERENCES chats(chat_id)
                ON DELETE CASCADE
                ON UPDATE CASCADE,

            CONSTRAINT rests_user_fk
                FOREIGN KEY (chat_id, user_id)
                REFERENCES users(chat_id, user_id)
                ON DELETE CASCADE
        );
    """)

    # Кастомные РП команды
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS rp_commands (
            chat_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            command TEXT NOT NULL,
            emoji TEXT NOT NULL,
            action TEXT NOT NULL,
            PRIMARY KEY (chat_id, user_id, command),

            -- Связи
            CONSTRAINT rp_commands_chat_fk
                FOREIGN KEY (chat_id)
                REFERENCES chats(chat_id)
                ON DELETE CASCADE
                ON UPDATE CASCADE,

            CONSTRAINT rp_commands_user_fk
                FOREIGN KEY (chat_id, user_id)
                REFERENCES users(chat_id, user_id)
                ON DELETE CASCADE
        );
    """)
