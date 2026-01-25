import asyncio
import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import ChatMember
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

logger = logging.getLogger(__name__)

# Глобальный семафор для ограничения количества одновременных запросов к Telegram API
_TG_API_SEMAPHORE = asyncio.Semaphore(20)


async def _with_tg_rate_limit(coro):
    """
    Выполняет корутину с ограничением rate limit Telegram API.

    Args:
        coro: Корутина для выполнения.

    Returns:
        Результат выполнения корутины.
    """
    async with _TG_API_SEMAPHORE:
        return await coro


async def _fetch_chat_member(
    bot: Bot,
    chat_id: int,
    user_id: int
) -> ChatMember:
    """
    Получает информацию об участнике чата.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.

    Returns:
        Объект ChatMember с информацией об участнике.

    Raises:
        TelegramBadRequest: Если чат или пользователь не найден.
        TelegramRetryAfter: При превышении rate limit.
    """
    return await bot.get_chat_member(chat_id, user_id)


async def _fetch_chat_member_with_retry(
    bot: Bot,
    chat_id: int,
    user_id: int
) -> ChatMember:
    """
    Получает информацию об участнике чата с автоматическим retry при rate limit.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.

    Returns:
        Объект ChatMember с информацией об участнике.
    """
    while True:
        try:
            return await _fetch_chat_member(bot, chat_id, user_id)
        except TelegramRetryAfter as e:
            logger.warning(
                f"Rate limit при получении участника {user_id} в чате {chat_id}. "
                f"Ожидание {e.retry_after} сек."
            )
            await asyncio.sleep(e.retry_after)


async def get_chat_member(
    bot: Bot,
    chat_id: int,
    user_id: int
) -> Optional[ChatMember]:
    """
    Получает информацию об участнике чата с обработкой ошибок.

    Функция безопасна для вызова - все возможные исключения
    Telegram API перехватываются и логируются.

    Args:
        bot: Экземпляр бота.
        chat_id: ID чата.
        user_id: ID пользователя.

    Returns:
        Объект ChatMember, если участник найден, иначе None.
    """
    try:
        return await _with_tg_rate_limit(
            _fetch_chat_member_with_retry(bot, chat_id, user_id)
        )
    except TelegramBadRequest as e:
        logger.warning(
            f"Не удалось получить участника {user_id} в чате {chat_id}: {e}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Неожиданная ошибка при получении участника {user_id} "
            f"в чате {chat_id}: {e}"
        )
        return None
