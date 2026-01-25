from typing import Optional
from aiogram import Bot
from aiogram.types import User

from services.telegram.chat_member import get_chat_member
from db.users import get_uid
from db.users.nicknames import get_nickname


async def mention_user(
    bot: Bot,
    chat_id: int,
    *,
    user_entity: Optional[User] = None,
    user_id: Optional[int] = None,
    user_username: Optional[str] = None,
) -> str:
    """
    Возвращает HTML-упоминание пользователя в чате.

    Функция автоматически определяет способ создания упоминания:
    1. Если передан готовый объект User - использует его
    2. Если передан только user_id - получает данные из чата
    3. Если передан только username - ищет user_id в базе
    4. В качестве имени используется никнейм (если есть) или full_name

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_entity: Готовый объект User (опционально).
        user_id: ID пользователя (опционально).
        user_username: Username пользователя без @ (опционально).

    Returns:
        HTML-строка с упоминанием пользователя.
        Возвращает "неизвестный пользователь", если определить не удалось.
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
        member = await get_chat_member(
            bot=bot,
            chat_id=chat_id,
            user_id=user_id
        )
        if member:
            user_entity = member.user

    # 4. Получаем никнейм (если доступен)
    nickname = None
    if not user_id and user_entity:
        user_id = user_entity.id

    if user_id:
        nickname = await get_nickname(chat_id=chat_id, user_id=user_id)

    # 5. Если после всего user_entity всё ещё нет — возвращаем безопасный текст
    if not user_entity:
        # Если есть id, пробуем отметить самостоятельно
        if user_id:
            return f'<a href="tg://user?id={user_id}">{nickname or f"@{user_id}"}</a>'

        return "неизвестный пользователь"

    # 6. Возвращаем форматированное HTML-упоминание
    name = nickname or user_entity.full_name or "неизвестный пользователь"

    return user_entity.mention_html(name=name)
