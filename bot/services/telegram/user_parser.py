from aiogram import Bot
from aiogram.types import Message, User
from typing import Optional, Tuple

from services.telegram.chat_member import get_chat_member
from db.users import get_uid

async def parse_user_mention(bot: Bot, msg: Message) -> Optional[User]:
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


async def parse_user_mention_and_clean_text(bot: Bot, msg: Message) -> Tuple[Optional[User], Optional[str]]:
    """
    Парсит пользователя из сообщения и возвращает текст без упоминания этого пользователя.
    """
    user = None
    clean_text = msg.text

    if msg.entities:
        for entity in msg.entities:
            if entity.type == "text_mention" and entity.user:
                user = entity.user
                # удаляем текст упоминания
                start, end = entity.offset, entity.offset + entity.length
                clean_text = msg.text[:start] + msg.text[end:]
                break
            elif entity.type == "mention":
                username = msg.text[entity.offset + 1: entity.offset + entity.length]
                try:
                    uid = await get_uid(int(msg.chat.id), username)
                    if uid:
                        member = await get_chat_member(bot=bot, chat_id=msg.chat.id, user_id=uid)
                        if member:
                            user = member.user
                            # удаляем текст упоминания
                            start, end = entity.offset, entity.offset + entity.length
                            clean_text = msg.text[:start] + msg.text[end:]
                            break
                except:
                    pass

    # убираем лишние пробелы после удаления
    if clean_text: clean_text = clean_text.strip()
    return user, clean_text
