from aiogram import Bot
from aiogram.types import User

from services.telegram.chat_member import get_chat_member
from db.users import get_uid
from db.users.nicknames import get_nickname

async def mention_user(
    bot: Bot,
    chat_id: int,
    *,
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
    elif not user_id and user_username:
        user_id = await get_uid(chat_id=chat_id, username=user_username)
        if not user_id:
            # fallback: не нашли id — просто вернем @username
            return f"@{user_username}"

    # 3. Если нет user_entity, но есть user_id, пытаемся получить entity из чата.
    elif user_id:
        # 
        member = await get_chat_member(bot=bot, chat_id=chat_id, user_id=user_id)
        if member:
            user_entity = member.user

    # 4. Получаем никнейм (если доступен)
    nickname = None
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
