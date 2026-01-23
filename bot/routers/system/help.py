from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from middlewares.maintenance import MaintenanceMiddleware
from utils.telegram.message_templates import send_welcome_message

router = Router(name="help")
router.message.middleware(MaintenanceMiddleware())
router.callback_query.middleware(MaintenanceMiddleware())


@router.message(Command("start", "help"))
async def help_handler(msg: Message):
    """Команда: /help"""
    bot = msg.bot

    await send_welcome_message(bot=bot,
                               chat_id=msg.chat.id,
                               private_msg=not (msg.chat.type in ("group", "supergroup"))
    )

