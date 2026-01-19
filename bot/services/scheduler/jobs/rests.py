from aiogram import Bot

from db.users.rests import expire_rests as _expire_rests
from services.telegram.user_mention import mention_user

async def expire_rests(bot: Bot):
    users = await _expire_rests()
    if not users: return

    for u in users:
        mention = await mention_user(bot=bot, chat_id=u["chat_id"], user_id=u["user_id"])
        if mention:
            text = f"⏰ {mention}, ваш рест подошёл к концу. Добро пожаловать обратно!"
            await bot.send_message(
                chat_id=u["chat_id"], text=text, parse_mode="HTML")
