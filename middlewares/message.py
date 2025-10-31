import time
from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from config import PRODUCTION, DEVELOPERS_ID
from db import upsert_user, add_message
from utils.telegram.media import get_quotable_media_id

class MessageOnlyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        # Это будет выполняться для каждого сообщения
        if (isinstance(event, Message)
                    and event.from_user
                    and event.chat.type in ["group", "supergroup"]
                    and not event.from_user.is_bot):
            
            user = event.from_user
            chat = event.chat
            await upsert_user(int(chat.id), int(user.id),
                              user.username, user.first_name)

            quotable_media_id = await get_quotable_media_id(event)

            file_id = quotable_media_id["file_id"] if quotable_media_id else None
            name = event.forward_sender_name or user.full_name
            is_forward = bool(event.forward_from or event.forward_sender_name)
            date = event.date.timestamp() or time.time()
            text = event.text or event.caption or ""
            
            await add_message(int(event.message_id), int(chat.id),
                    int(user.id), name,
                    text, date, is_forward,
                    file_id=file_id
            )

        # Продолжаем выполнение хэндлера только если сейчас на продакшене
        if PRODUCTION or int(user.id) in DEVELOPERS_ID:
            return await handler(event, data)
