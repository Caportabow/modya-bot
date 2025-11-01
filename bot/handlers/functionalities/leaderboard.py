from aiogram import Router, F
from aiogram.types import Message

from utils.telegram.users import mention_user
from utils.time import get_since
from db.leaderboard import user_leaderboard

router = Router(name="leaderboard")


@router.message((F.text.lower().startswith("топ")) & (F.chat.type.in_(["group", "supergroup"])))
async def stats_handler(msg: Message):
    """Команда: топ [день|неделя|месяц|год|вся]"""
    bot = msg.bot
    parts = msg.text.split()
    period = parts[1] if len(parts) > 1 else "вся"

    try:
        since, beauty_since = get_since(period)
    except ValueError:
        return
    
    top = await user_leaderboard(int(msg.chat.id), since=since)
    ans = f"📊 Топ сообщений за {beauty_since}:\n\n"
    msg_count = 0

    for i, u in enumerate(top):
        mention = await mention_user(bot=bot, chat_id=int(msg.chat.id), user_id=int(u["user_id"]))
        
        ans += f"{i+1}. {mention} - {u["count"]}\n"
        msg_count += u["count"]
    ans += f"\nВсего сообщений: {msg_count}"

    await msg.reply(ans, parse_mode="HTML")
