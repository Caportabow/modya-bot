import random
from aiogram import Router, F
from aiogram.types import Message

from db.users.rp_commands import get_user_rp_commands

from services.process_roleplay import parse_rp_command
from services.telegram.user_parser import parse_user_mention_and_clean_text
from utils.telegram.message_templates import send_random_sticker_quote

router = Router(name="groups")


@router.message(F.chat.type.in_(["group", "supergroup"]))
async def on_message(msg: Message):
    # Пробуем обработать как RP команду
    bot = msg.bot
    user = msg.from_user
    chat = msg.chat
    text = msg.text or msg.caption

    if text and user and bot:
        # Удаляем префиксы
        prefixes = ["!", "/", "-", "—", "."]
        text = text.lstrip("".join(prefixes))

        if msg.reply_to_message and msg.reply_to_message.from_user:
            # Реплай на пользователя
            target_user_entity = msg.reply_to_message.from_user
        else:
            # Упоминание пользователя в тексте
            target_user_entity, text = await parse_user_mention_and_clean_text(bot, msg)
            # Если target_user_entity стал None, то действие направлено на самих нас

        user_rp_commands = await get_user_rp_commands(int(chat.id), int(user.id))
        command = await parse_rp_command(
            bot, int(chat.id), text,
            user, target_user_entity, user_rp_commands
        )

        if command:
            await (msg.reply_to_message or msg).reply(command, parse_mode="HTML")
            return # если это ролевое сообщение, не продолжаем дальше
    
    # выдача рандомной цитаты
    if random.random() < 0.005:  # ~0.5% шанс
        await send_random_sticker_quote(msg)
