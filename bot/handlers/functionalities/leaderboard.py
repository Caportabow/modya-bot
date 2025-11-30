from aiogram import Router, F
from aiogram.types import Message

from datetime import timedelta, datetime, timezone

from utils.telegram.users import mention_user_with_delay
from utils.time import get_duration, format_timedelta
from db.leaderboard import user_leaderboard

router = Router(name="leaderboard")


@router.message((F.text.lower().startswith("топ")) & (F.chat.type.in_(["group", "supergroup"])))
async def stats_handler(msg: Message):
    """Команда: топ {период}"""
    bot = msg.bot
    parts = msg.text.split()

    # Проверяем, указан ли период пользователем
    if len(parts) > 1:
        duration = get_duration(" ".join(parts[1:]))

        # parts[0].lower() == "топ" нужно для избежания моментов когда юзер
        # пишет что-то по типу Топовый ПК, а бот реагирует на это
        if duration is None and parts[0].lower() == "топ":
            await msg.reply("❌ Не удалось распознать период.")
            return
    else:
        duration = "forever"

    # Определяем временной диапазон
    if isinstance(duration, timedelta):
        since = datetime.now(timezone.utc) - duration
        beauty_since = format_timedelta(duration, adder=False)
    else:
        since = None
        beauty_since = "всё время"
    
    limit = 15
    top = await user_leaderboard(int(msg.chat.id), limit=limit, since=since)
    if not top or len(top) == 0:
        await msg.reply("❌ Недостаточно информации.")
        return
    
    ans = f"📊 Топ{(' ' + str(limit)) if len(top) == limit else ''} пользователей за {beauty_since}:\n\n"
    msg_count = 0

    for i, u in enumerate(top):
        mention = await mention_user_with_delay(bot=bot, chat_id=int(msg.chat.id), user_id=int(u["user_id"]))
        
        ans += f"{i+1}. {mention} - {u["count"]}\n"
        msg_count += u["count"]
    ans += f"\nВсего сообщений: {msg_count}"

    await msg.reply(ans, parse_mode="HTML")
