import re
from aiogram import Router, F
from aiogram.types import Message

from bot.db.chats.settings import set_max_warns
from utils.telegram.users import is_admin

router = Router(name="chat_settings")

@router.message(
    (F.text.regexp(r"^\.\s*лимит варнов(?:\s|$)", flags=re.IGNORECASE)) & 
    (F.chat.type.in_(["group", "supergroup"]))
)
async def set_nick(msg: Message):
    """Команда: .лимит варнов кол-во"""
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.reply("❌ Укажите желаемый лимит варнов")
        return
    
    max_warns = parts[2].strip()
    if not max_warns.isdigit():
        await msg.reply("❌ Укажите корректное число")
        return

    max_warns = int(max_warns)

    if max_warns < 1:
        await msg.reply("❌ Минимальный лимит варнов — 1")
        return
    elif max_warns > 100:
        await msg.reply("❌ Максимальный лимит варнов — 100")
        return

    access = await is_admin(bot=msg.bot, chat_id=int(msg.chat.id), user_id=int(msg.from_user.id))
    if not access:
        await msg.reply("❌ Только администраторы могут изменять лимит варнов")
        return

    await set_max_warns(int(msg.chat.id), max_warns)
    await msg.reply(f"📛 Новое максимальное кол-во варнов: {max_warns}")
