from aiogram import Bot
from aiogram.types import Message

from services.telegram_chat_member import get_chat_member
from db.users import get_uid

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
                        member = await get_chat_member(bot=bot, chat_id=msg.chat.id, user_id=uid)
                        if member:
                            user = member.user
                            break
                except:
                    pass
    return user
