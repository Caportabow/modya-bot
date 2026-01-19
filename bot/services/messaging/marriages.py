from datetime import datetime, timezone
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from services.telegram.user_mention import mention_user
from db.marriages import get_marriages

from services.time_utils import TimedeltaFormatter
from services.telegram.keyboards.pagination import get_pagination_keyboard

async def generate_all_marriages_msg(bot: Bot, chat_id: int, page: int) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    data = await get_marriages(chat_id, page)
    if not data:
        return None, None

    marriages = data["data"]
    now = datetime.now(timezone.utc)
    ans = f"💕 Пары нашего чата:\n\n"

    ans += "<blockquote expandable>"
    for i, m in enumerate(marriages):
        mention_1 = await mention_user(bot=bot, chat_id=chat_id, user_id=int(m["participants"][0]))
        mention_2 = await mention_user(bot=bot, chat_id=chat_id, user_id=int(m["participants"][1]))
        
        date = f"{m['date']:%d.%m.%Y} ({TimedeltaFormatter.format(now - m['date'], suffix='none')})"
        line = f"• {mention_1} & {mention_2}\n   └ Вместе с {date}\n\n"
        
        ans += line
    ans += "</blockquote>"

    pagination = data["pagination"]
    keyboard = await get_pagination_keyboard(
        subject = "all_marriages", query=None, next_page=pagination["next_page"],
        prev_page=pagination["prev_page"]
    )

    return ans, keyboard
