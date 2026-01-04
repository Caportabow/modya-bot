import asyncio
from aiogram import Bot
from datetime import datetime, timezone

from db.chats.cleaning import do_cleaning, fetch_chats_for_scheduled_cleaning, update_last_cleaning_time
from utils.telegram.message_templates import generate_cleaning_messages


async def run_scheduled_cleanings(bot: Bot):
    """Запускает чистку для всех чатов с включенной автоматической чисткой."""
    now = datetime.now(timezone.utc)

    chats = await fetch_chats_for_scheduled_cleaning()
    for chat_id in chats:
        result = await do_cleaning(int(chat_id))
        await update_last_cleaning_time(int(chat_id))

        # Генерируем сообщение об чистке
        messages = await generate_cleaning_messages(
            bot=bot,
            chat_id=chat_id,
            cleaning_result=result
        )
        messages[0] = "⚙️ Запланированная чистка:\n\n" + messages[0]

        # Рассылаем сообщения
        for text in messages:
            await bot.send_message(chat_id=int(chat_id), text=text, parse_mode="HTML")
            await asyncio.sleep(0.1)
