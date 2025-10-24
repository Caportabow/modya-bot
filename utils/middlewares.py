import time
from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from db import upsert_user, add_message
from utils.media import get_quotable_media_id

class AllMessagesMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        # Это будет выполняться для каждого сообщения
        user = event.from_user
        chat = event.chat
        if user and chat.type in ["group", "supergroup"]:
            await upsert_user(int(chat.id), int(user.id), user.username, user.first_name)

            quotable_media_id = await get_quotable_media_id(event)

            file_id = quotable_media_id["file_id"] if quotable_media_id else None
            date = event.date.timestamp() or time.time()
            text = event.text or event.caption or ""
            
            await add_message(int(event.message_id), int(chat.id),
                    int(user.id), user.full_name,
                    text, date,
                    file_id=file_id
            )

        # Продолжаем выполнение хэндлера
        return await handler(event, data)

def setup_middlewares(dp):
    dp.message.middleware(AllMessagesMiddleware())
    
    return dp
