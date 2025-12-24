import random
from aiogram import Router, F
from aiogram.types import Message

from utils.telegram.message_templates import process_roleplay_message, send_random_sticker_quote

router = Router(name="groups")


@router.message(F.chat.type.in_(["group", "supergroup"]))
async def on_message(msg: Message):
    # Пробуем обработать как RP команду
    is_roleplay_command = await process_roleplay_message(msg)
    if is_roleplay_command: return # если это ролевое сообщение, не продолжаем дальше
    
    # выдача рандомной цитаты
    if random.random() < 0.005:  # ~0.5% шанс
        await send_random_sticker_quote(msg)
