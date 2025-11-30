import asyncio
from aiogram import Bot
from aiogram.types import Message, User
from aiogram.exceptions import TelegramBadRequest

from db.users import get_uid
from db.users.nicknames import get_nickname

async def get_chat_member_or_fall(bot: Bot, chat_id: int, user_id: int):
    """Пытается получить информацию о пользователе в чате, возвращает None при ошибке."""
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    except TelegramBadRequest as e:
        print(f"⚠️ Failed to get chat member {user_id} in chat {chat_id}: {e}")
        return None
    
    return member

async def mention_user(
    bot: Bot,
    *,
    chat_id: int | None = None,
    user_entity: User | None = None,
    user_id: int | None = None,
    user_username: str | None = None,
) -> str:
    """
    Возвращает HTML-упоминание пользователя в чате.
    Если невозможно определить пользователя — возвращает 'неизвестный' или @username.
    """
    # 1. Если есть готовый объект пользователя — используем его напрямую.
    if user_entity:
        user_id = user_entity.id

    # 2. Если нет user_id, но есть username — пробуем получить id из базы
    elif not user_id and user_username and chat_id:
        user_id = await get_uid(chat_id=chat_id, username=user_username)
        if not user_id:
            # fallback: не нашли id — просто вернем @username
            return f"@{user_username}"

    # 3. Если нет user_entity, но есть user_id, пытаемся получить entity из чата.
    elif user_id and chat_id:
        # 
        member = await get_chat_member_or_fall(bot=bot, chat_id=chat_id, user_id=user_id)
        if member:
            user_entity = member.user

    # 4. Получаем никнейм (если доступен)
    nickname = None
    if chat_id:
        if not user_id and user_entity: user_id = user_entity.id
        
        if user_id: nickname = await get_nickname(chat_id=chat_id, user_id=user_id)

    # 5. Если после всего user_entity всё ещё нет — возвращаем безопасный текст
    if not user_entity:
        # Если есть id, пробуем отметить самостоятельно
        if user_id:
            return f'<a href="tg://user?id={user_id}">{nickname or f"@{user_id}"}</a>'

        return "неизвестный пользователь"

    # 6. Возвращаем форматированное HTML-упоминание
    name = nickname or user_entity.full_name or "неизвестный пользователь"
    return user_entity.mention_html(name=name)

async def mention_user_with_delay(bot, chat_id, user_id):
    await asyncio.sleep(0.15) # or random.randrange(15, 30) / 100
    return await mention_user(bot=bot, chat_id=chat_id, user_id=user_id)

async def parse_user_mention(bot: Bot, msg: Message):
    """Парсит пользователя из сообщения."""
    user = None
    if msg.entities:
        for entity in msg.entities:
            if entity.type == "text_mention" and entity.user:
                user = entity.user
                break
            elif entity.type == "mention":
                username = msg.text[entity.offset + 1: entity.offset + entity.length]
                try:
                    uid = await get_uid(int(msg.chat.id), username)

                    if uid:
                        member = await get_chat_member_or_fall(bot=bot, chat_id=msg.chat.id, user_id=uid)
                        if member:
                            user = member.user
                            break
                except:
                    pass
    return user

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором чата."""
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)

        return (
            member.status == "creator" or
            (member.status == "administrator" and member.can_restrict_members)
        ) if member else False
    except:
        return False
    
async def is_creator(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Проверяет, является ли пользователь создателем чата."""
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)

        return member.status == "creator" if member else False
    except:
        return False
