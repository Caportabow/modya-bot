from datetime import datetime, timezone
from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from db.users import upsert_user
from db.messages import add_message

from services.telegram.media import get_quotable_media_id

class MessageOnlyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Это будет выполняться для каждого сообщения
        if (isinstance(event, Message)
                and event.from_user
                and event.chat.type in ["group", "supergroup"]
                and not event.from_user.is_bot
                and not event.left_chat_member
                and not event.new_chat_members):
            user = event.from_user
            chat = event.chat
            await upsert_user(int(chat.id), int(user.id),
                              user.first_name, user.username)

            quotable_media_id = await get_quotable_media_id(event)

            file_id = quotable_media_id["file_id"] if quotable_media_id else None
            name = event.forward_sender_name or user.full_name

            forward_user_id = event.forward_from.id if event.forward_from else (1 if event.forward_sender_name else None)

            date = event.date or datetime.now(timezone.utc)
            text = event.text or event.caption or ""
            
            await add_message(int(event.message_id), int(chat.id),
                    int(user.id), date, name,
                    text, forward_user_id=forward_user_id,
                    file_id=file_id
            )
        
        return await handler(event, data)

