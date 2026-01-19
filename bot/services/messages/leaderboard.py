from typing import Tuple, Optional
from datetime import datetime, timedelta, timezone
from aiogram.types import InlineKeyboardMarkup

from services.telegram.user_mention import mention_user
from utils.time import TimedeltaFormatter, serialize_timedelta
from services.telegram.keyboards.pagination import get_pagination_keyboard
from db.leaderboard import user_leaderboard

async def generate_leaderboard_msg(bot, chat_id: int, page: int, duration: Optional[timedelta]) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    if duration:
        since = datetime.now(timezone.utc) - duration
        beauty_since = TimedeltaFormatter.format(duration, suffix="none")
    else:
        since = None
        beauty_since = "всё время"

    per_page = 20
    data = await user_leaderboard(chat_id, since=since, page=page, per_page=per_page)
    if not data:
        return None, None
    top = data["data"]
    
    msg_count = sum(u["count"] for u in top)
    ans = f"📊 Топ активности за {beauty_since}:\n\n"

    adder = per_page * (page - 1)
    ans += "<blockquote expandable>"
    for i, u in enumerate(top):
        mention = await mention_user(bot=bot, chat_id=chat_id, user_id=int(u["user_id"]))
        
        percentage = (u["count"] / msg_count * 100) if msg_count > 0 else 0
        
        ans += f"{adder+i+1} {mention}: {u['count']} (вклад: {percentage:.1f}%)\n"
    ans += "</blockquote>"

    ans += f"\n💬 Итого: {msg_count}"

    pagination = data["pagination"]
    keyboard = await get_pagination_keyboard(
        subject = "leaderboard", query=serialize_timedelta(duration) if duration else None, next_page=pagination["next_page"],
        prev_page=pagination["prev_page"]
    )

    return ans, keyboard
