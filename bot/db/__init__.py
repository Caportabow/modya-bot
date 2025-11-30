import asyncpg
from contextlib import asynccontextmanager
from config import DATABASE_URL


pool: asyncpg.Pool | None = None


async def init_db():
    """Создаёт пул соединений при запуске приложения."""
    global pool
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=5,
        command_timeout=100  # чтобы не зависало при долгих запросах
    )
    print("✅ Database pool created")

    # Создаём таблицы, если их нет
    async with pool.acquire() as conn:
        await create_tables(conn)
        print("📦 Tables checked/created")


async def close_db():
    """Закрывает пул при завершении."""
    global pool
    if pool is not None:
        await pool.close()
        print("🔒 Database pool closed")


@asynccontextmanager
async def connection():
    """Асинхронный контекстный менеджер для безопасного доступа к БД."""
    if pool is None:
        raise RuntimeError("Database pool is not initialized. Call init_db() first.")
    async with pool.acquire() as conn:
        yield conn


# Упрощённые функции для выполнения запросов

async def fetchmany(query: str, *args):
    """Возвращает список записей (аналог cursor.fetchall())."""
    async with connection() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]


async def fetchone(query: str, *args):
    """Возвращает одну запись (аналог cursor.fetchone())."""
    async with connection() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetchval(query: str, *args):
    """Возвращает только одно значение (аналог cursor.fetchval())."""
    async with connection() as conn:
        val = await conn.fetchval(query, *args)
        return val or None

async def case(query: str, *args):
    """Выполняет CASE запросы (аналог cursor.fetchval())."""
    async with connection() as conn:
        val = await conn.fetchval(query, *args)
        return bool(val)

async def count(query: str, *args):
    """Выполняет COUNT запросы (аналог cursor.fetchval())."""
    async with connection() as conn:
        val = await conn.fetchval(query, *args)
        return val or 0

@asynccontextmanager
async def transaction():
    """Создаёт транзакцию и возвращает connection."""
    async with connection() as conn:
        async with conn.transaction():
            yield conn

async def execute(query: str, *args):
    """Выполняет INSERT/UPDATE/DELETE без возврата данных."""
    async with connection() as conn:
        return await conn.execute(query, *args)



# ----------------------------------------------------
# 🧱 Создание таблиц
# ----------------------------------------------------

async def create_tables(conn: asyncpg.Connection):
    """Создаёт нужные таблицы, если их ещё нет."""
    # Чаты
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id BIGINT NOT NULL,
            PRIMARY KEY (chat_id)  
        );
    """)

    # Браки
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS marriages (
            id BIGSERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            date TIMESTAMPTZ NOT NULL,
            
            -- Relations
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
            rest TIMESTAMPTZ DEFAULT NULL,
            marriage_id BIGINT DEFAULT NULL,
            parent_marriage_id BIGINT DEFAULT NULL,
            adoption_date TIMESTAMPTZ DEFAULT NULL,
            PRIMARY KEY (chat_id, user_id),
            
            -- Relations
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
            
            -- Relations
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
            sticker_file_id TEXT NOT NULL UNIQUE,
            
            -- Relations
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

            -- Relations
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

            -- Relations
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
