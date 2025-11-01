from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from utils.telegram.message_templates import send_welcome_message

router = Router(name="help")


@router.message(Command("start", "help"))
async def help_handler(msg: Message):
    """Команда: /help"""
    bot = msg.bot

    if msg.chat.type in ("group", "supergroup"):
        await send_welcome_message(bot=bot, chat_id=msg.chat.id)
    else:
        await send_welcome_message(bot=bot, chat_id=msg.chat.id, private_msg=True)

