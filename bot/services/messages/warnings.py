from datetime import datetime, timezone
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import User, InlineKeyboardMarkup

from services.telegram.user_mention import mention_user
from db.warnings import get_all_warnings, get_user_warnings
from db.chats.settings import get_max_warns

from utils.time import TimedeltaFormatter
from utils.telegram.keyboards import get_pagination_keyboard


async def generate_all_warnings_msg(bot: Bot, chat_id: int, page: int) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    data = await get_all_warnings(chat_id, page)
    if not data:
        return None, None
    
    users_with_warnings = data["data"]
    max_warns = await get_max_warns(chat_id)

    ans = f"📛 Список предупреждений:\n\n"

    ans += "<blockquote expandable>"
    for i, u in enumerate(users_with_warnings):
        mention = await mention_user(bot=bot, chat_id=chat_id, user_id=int(u["user_id"]))
        line = f"• {mention} - {u['count']}/{max_warns}\n"
        
        ans += line
    ans += "</blockquote>"

    pagination = data["pagination"]
    keyboard = await get_pagination_keyboard(
        subject = "all_warnings", query=None, next_page=pagination["next_page"],
        prev_page=pagination["prev_page"]
    )
    
    return ans, keyboard

async def generate_user_warnings_msg(bot: Bot, chat_id: int, target_user: User, page: int, with_back_button: bool = False) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    per_page = 10
    data = await get_user_warnings(chat_id, int(target_user.id), page, per_page)
    if not data:
        return None, None

    warnings = data["data"]
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    warnings_count = len(warnings)
    max_warns = await get_max_warns(int(chat_id))

    ans = f"⚠️ Варны пользователя {mention} ({warnings_count}/{max_warns}):\n\n"

    adder = per_page * (page - 1)
    ans += "<blockquote expandable>"
    for i, w in enumerate(warnings):
        reason = w["reason"] or "Причина не указана."
        date = TimedeltaFormatter.format(datetime.now(timezone.utc) - w["assignment_date"])
        moderator_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=w["administrator_user_id"])
        formatted_expire_date = TimedeltaFormatter.format(w["expire_date"] - datetime.now(timezone.utc), suffix="none") if w["expire_date"] else "навсегда"

        ans += f"┌ Варн #{adder+i+1}\n├ Срок: {formatted_expire_date}\n├ Причина: {reason}\n├ Модератор: {moderator_mention}\n└ Выдан: {date}\n\n"
    ans += "</blockquote>"

    pagination = data["pagination"]
    keyboard = await get_pagination_keyboard(
        subject = "user_warnings", query=int(target_user.id), next_page=pagination["next_page"],
        prev_page=pagination["prev_page"], back_button_active=with_back_button
    )

    return ans, keyboard
