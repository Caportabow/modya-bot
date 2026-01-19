from aiogram import Bot
from datetime import datetime, timezone

from db.chats.cleaning import fetch_chats_for_scheduled_cleaning, update_last_cleaning_time
from services.messaging.cleaning import generate_cleaning_msg


async def run_cleanings(bot: Bot):
    """Запускает чистку для всех чатов с включенной автоматической чисткой."""
    now = datetime.now(timezone.utc)

    chats = await fetch_chats_for_scheduled_cleaning()
    for chat_id in chats:
        await update_last_cleaning_time(int(chat_id))

        text, keyboard = await generate_cleaning_msg(bot, int(chat_id), 1)
        await bot.send_message(chat_id=int(chat_id), text=text, parse_mode="HTML", reply_markup=keyboard)
