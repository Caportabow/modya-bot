from datetime import datetime, timezone
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import User, InlineKeyboardMarkup

from services.telegram.user_mention import mention_user
from db.users.rests import get_all_rests, get_user_rest

from utils.time import TimedeltaFormatter
from utils.telegram.keyboards import get_pagination_keyboard

async def generate_all_rests_msg(bot: Bot, chat_id: int, page: int) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    data = await get_all_rests(chat_id, page=page)

    if not data:
        return None, None
    rests = data["data"]

    now = datetime.now(timezone.utc)
    ans_header = f"⏰ Пользователи в ресте:\n\n"
    ans = ans_header

    ans += "<blockquote expandable>"
    for i, r in enumerate(rests):
        mention = await mention_user(bot=bot, chat_id=chat_id, user_id=int(r["user_id"]))
        rest_info = f"до {r['valid_until']:%d.%m.%Y} (еще {TimedeltaFormatter.format(r['valid_until'] - now, suffix="none")})"
        line = f"• {mention} - {rest_info}\n"

        ans += line
    ans += "</blockquote>"

    pagination = data["pagination"]
    keyboard = await get_pagination_keyboard(
        subject = "all_rests", query=None, next_page=pagination["next_page"],
        prev_page=pagination["prev_page"]
    )

    return ans, keyboard

async def generate_rest_description_msg(bot: Bot, chat_id: int, target_user_entity: User) -> Optional[str]:
    rest = await get_user_rest(chat_id, int(target_user_entity.id))
    if not rest:
        return None

    now = datetime.now(timezone.utc)
    beauty_until = TimedeltaFormatter.format(rest['valid_until'] - now, suffix="none")
    beauty_assignment_date = TimedeltaFormatter.format(now - rest['assignment_date'])
    user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user_entity)
    administrator_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=rest['administrator_user_id'])

    ans = f"⏰ Рест пользователя {user_mention}.\n"
    ans += f"🗓 Взят: {rest['assignment_date']:%d.%m.%Y} ({beauty_assignment_date})\n"
    ans += f"📅 Действителен до: {rest['valid_until']:%d.%m.%Y} (еще {beauty_until})\n"
    ans += f"👮 Администратор: {administrator_mention}."
    
    return ans
