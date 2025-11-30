from aiogram import Router, F
from aiogram.types import Message

from random import random

from db.quotes import get_random_quote
from utils.roleplay import parse_rp_command

router = Router(name="groups")


@router.message(F.chat.type.in_(["group", "supergroup"]))
async def on_message(msg: Message):
    bot = msg.bot
    user = msg.from_user
    chat = msg.chat

    # рп команды
    text = msg.text or msg.caption
    if text:
        # Удаляем префиксы
        prefixes = ["!", "/", "-", "—", "."]
        text = text.lstrip("".join(prefixes))

        target_user_entity = None
        reply_message = msg.reply_to_message or msg
        target_user_entity = reply_message.from_user
        
        if not target_user_entity and msg.entities:
            # Пытаемся найти упоминание пользователя в тексте
            for entity in msg.entities:
                if entity.type == "text_mention" and entity.user:
                    target_user_entity = entity.user

        command = await parse_rp_command(
            bot, int(chat.id), text,
            user, target_user_entity
        )

        if command:
            await reply_message.reply(command, parse_mode="HTML")
            return
    
    # выдача рандомной цитаты
    if random() < 0.005:  # ~0.1% шанс
        quote_sticker_id = await get_random_quote(int(msg.chat.id))

        if quote_sticker_id:
            await msg.reply_sticker(sticker=quote_sticker_id)
