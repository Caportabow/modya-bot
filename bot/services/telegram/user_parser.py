import logging
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import Message, User
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

from services.telegram.chat_member import get_chat_member
from db.users import get_uid

logger = logging.getLogger(__name__)


async def parse_user_mention(bot: Bot, msg: Message) -> Optional[User]:
    """
    Парсит пользователя из сообщения по упоминанию.

    Ищет пользователя в следующем порядке:
    1. text_mention (прямая ссылка на пользователя)
    2. mention (@username)

    Args:
        bot: Экземпляр бота.
        msg: Сообщение для парсинга.

    Returns:
        Объект User, если найден, иначе None.
    """
    if not msg.entities:
        return None

    for entity in msg.entities:
        if entity.type == "text_mention" and entity.user:
            return entity.user

        if entity.type == "mention":
            username = msg.text[entity.offset + 1: entity.offset + entity.length]
            try:
                uid = await get_uid(int(msg.chat.id), username)
                if uid:
                    member = await get_chat_member(
                        bot=bot,
                        chat_id=msg.chat.id,
                        user_id=uid
                    )
                    if member:
                        return member.user
            except (TelegramBadRequest, TelegramRetryAfter) as e:
                logger.warning(
                    f"Ошибка при получении участника чата {username}: {e}"
                )
            except Exception as e:
                logger.error(
                    f"Неожиданная ошибка при парсинге @{username}: {e}"
                )

    return None


async def parse_user_mention_and_clean_text(
    bot: Bot,
    msg: Message
) -> Tuple[Optional[User], Optional[str]]:
    """
    Парсит пользователя из сообщения и возвращает очищенный текст.

    Извлекает пользователя и возвращает текст сообщения с удалённым
    упоминанием этого пользователя.

    Args:
        bot: Экземпляр бота.
        msg: Сообщение для парсинга.

    Returns:
        Кортеж (User, очищенный_текст). Если пользователь не найден,
        возвращает (None, исходный_текст).
    """
    if not msg.entities:
        return None, msg.text

    user = None
    clean_text = msg.text

    for entity in msg.entities:
        if entity.type == "text_mention" and entity.user:
            user = entity.user
            # Удаляем текст упоминания
            start, end = entity.offset, entity.offset + entity.length
            clean_text = msg.text[:start] + msg.text[end:]
            break

        if entity.type == "mention":
            username = msg.text[entity.offset + 1: entity.offset + entity.length]
            try:
                uid = await get_uid(int(msg.chat.id), username)
                if uid:
                    member = await get_chat_member(
                        bot=bot,
                        chat_id=msg.chat.id,
                        user_id=uid
                    )
                    if member:
                        user = member.user
                        # Удаляем текст упоминания
                        start, end = entity.offset, entity.offset + entity.length
                        clean_text = msg.text[:start] + msg.text[end:]
                        break
            except (TelegramBadRequest, TelegramRetryAfter) as e:
                logger.warning(
                    f"Ошибка при получении участника чата {username}: {e}"
                )
            except Exception as e:
                logger.error(
                    f"Неожиданная ошибка при парсинге @{username}: {e}"
                )

    # Убираем лишние пробелы после удаления
    if clean_text:
        clean_text = clean_text.strip()

    return user, clean_text
