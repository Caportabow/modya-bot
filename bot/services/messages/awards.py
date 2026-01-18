from datetime import datetime, timezone
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import User, InlineKeyboardMarkup

from db.awards import get_awards

from utils.time import TimedeltaFormatter
from utils.telegram.keyboards import get_pagination_keyboard
from utils.telegram.users import mention_user


async def generate_user_awards_msg(bot: Bot, chat_id: int, target_user: User, page: int, with_back_button: bool = False) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    per_page = 15
    data = await get_awards(chat_id, int(target_user.id), page, per_page)
    if not data:
        return None, None

    awards = data["data"]
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    ans = f"🏆 Награды пользователя {mention}:\n\n"

    adder = per_page * (page - 1)
    ans += "<blockquote expandable>"
    for i, a in enumerate(awards):
        award = a["award"]
        date = TimedeltaFormatter.format(datetime.now(timezone.utc) - a["assignment_date"])
        line = f"🎗 {adder+i+1}. {award} | {date}\n"

        ans += line
    ans += "</blockquote>"

    pagination = data["pagination"]
    keyboard = await get_pagination_keyboard(
        subject = "user_awards", query=int(target_user.id), next_page=pagination["next_page"],
        prev_page=pagination["prev_page"], back_button_active=with_back_button
    )

    return ans, keyboard
