import re
from aiogram import Router, F
from aiogram.types import Message

from datetime import timedelta, datetime, timezone

from utils.telegram.users import mention_user_with_delay
from utils.time import TimedeltaFormatter, DurationParser
from db.leaderboard import user_leaderboard

router = Router(name="leaderboard")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(
    F.text.regexp(r"^топ(?:\s|$)", flags=re.IGNORECASE)
)
async def stats_handler(msg: Message):
    """Команда: топ {период}"""
    bot = msg.bot
    parts = msg.text.split(maxsplit=1)

    if len(parts) > 1:
        duration = DurationParser.parse(parts[1].strip())

        if not duration:
            # аргумент не задан или пользователь указал "навсегда"
            if not DurationParser.parse_forever(parts[1].strip()):
                # команда вероятно сработала случайно, останавливаем обработку
                return
            
            # пользователь указал "навсегда"
            since = None
            beauty_since = "всё время"
        
        else:
            # время распарсилось корректно
            since = datetime.now(timezone.utc) - duration
            beauty_since = TimedeltaFormatter.format(duration, suffix="none")
    
    else:
        # Если аргумента нет - смотрим за всё время
        since = None
        beauty_since = "всё время"

    limit = 30
    top = await user_leaderboard(int(msg.chat.id), limit=limit, since=since)
    if not top or len(top) == 0:
        await msg.reply("❌ Недостаточно информации.")
        return
    
    ans = f"📊 Топ активности за {beauty_since}:\n\n"
    ans += "<blockquote expandable>"
    msg_count = sum(u["count"] for u in top)

    for i, u in enumerate(top):
        mention = await mention_user_with_delay(bot=bot, chat_id=int(msg.chat.id), user_id=int(u["user_id"]))
        
        percentage = (u["count"] / msg_count * 100) if msg_count > 0 else 0
        
        ans += f"{i+1} {mention}: {u['count']} ({percentage:.1f}%)\n"

    ans += "</blockquote>"
    ans += f"\n💬 Итого: {msg_count}"

    await msg.reply(ans, parse_mode="HTML")
