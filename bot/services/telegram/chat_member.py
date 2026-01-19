import asyncio
from typing import Optional
from aiogram import Bot
from aiogram.types import ChatMember
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

# Общий семафор
_TG_API_SEMAPHORE = asyncio.Semaphore(20)
async def with_tg_rate_limit(coro):
    async with _TG_API_SEMAPHORE:
        return await coro

async def fetch_chat_member(
    bot: Bot,
    chat_id: int,
    user_id: int,
) -> ChatMember:
    """Враппер на bot.get_chat_member."""
    return await bot.get_chat_member(chat_id, user_id)

async def fetch_chat_member_with_retry(bot: Bot, chat_id: int, user_id: int) -> ChatMember:
    """Пытается получить информацию о пользователе в чате, при рейт лимите повторяет попытку через время."""
    while True:
        try:
            return await fetch_chat_member(bot, chat_id, user_id)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)

async def get_chat_member(bot: Bot, chat_id: int, user_id: int) -> Optional[ChatMember]:
    """Пытается получить информацию о пользователе в чате, возвращает None при ошибке."""
    try:
        return await with_tg_rate_limit(
            fetch_chat_member_with_retry(bot, chat_id, user_id)
        )
    except TelegramBadRequest as e:
        print(f"⚠️ Failed to get chat member {user_id} in chat {chat_id}: {e}")
        return None
