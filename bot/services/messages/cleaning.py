from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from db.chats.cleaning import check_cleaning_accuracy, minmsg_users, inactive_users, do_cleaning

from utils.telegram.keyboards import serialize_timedelta
from utils.time import TimedeltaFormatter
from utils.telegram.keyboards import get_pagination_keyboard
from utils.telegram.users import mention_user

async def generate_minmsg_msg(bot: Bot, chat_id: int, page: int, msg_count: int) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    cleaning_accuracy = await check_cleaning_accuracy(chat_id)
    warning = "" if cleaning_accuracy else "\n<i>ℹ️ Бот в чате недавно, статистика может быть неполной.</i>"

    data = await minmsg_users(chat_id, msg_count, page=page)

    if not data or len(data["data"]) == 0:
        return None, None
    
    users = data["data"]

    ans_header = f"⚠️ Не набрали норму ({msg_count} сообщ.):{warning}\n\n"
    ans = ans_header
    ans += "<blockquote expandable>"

    for i, u in enumerate(users):
        mention = await mention_user(bot=bot, chat_id=chat_id, user_id=int(u["user_id"]))
        
        percentage = (u['count'] / msg_count) * 100
        line = f"• {mention}: {u['count']} ({percentage:.0f}%)\n"

        ans += line
    ans += "</blockquote>"

    pagination = data["pagination"]
    keyboard = await get_pagination_keyboard(
        subject = "minmsg", query=msg_count, next_page=pagination["next_page"],
        prev_page=pagination["prev_page"]
    )

    return ans, keyboard


async def generate_inactive_msg(bot: Bot, chat_id: int, page: int, duration: timedelta) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    cleaning_accuracy = await check_cleaning_accuracy(chat_id)
    warning = "" if cleaning_accuracy else "\n<i>ℹ️ Бот в чате недавно, статистика может быть неполной.</i>"

    data = await inactive_users(chat_id, duration, page)

    if not data:
        return None, None
    
    users = data["users"]

    now = datetime.now(timezone.utc)
    ans_header = f"💤 Неактивны последние {TimedeltaFormatter.format(duration, suffix='none')}:{warning}\n\n"
    ans = ans_header
    ans += "<blockquote expandable>"

    for i, u in enumerate(users):
        mention = await mention_user(bot=bot, chat_id=chat_id, user_id=int(u["user_id"]))

        date = TimedeltaFormatter.format(now - u["last_message_date"], suffix="none") if u["last_message_date"] else "никогда"
        line = f"• {mention}: уже {date}\n"
        ans += line
    ans += "</blockquote>"

    pagination = data["pagination"]
    keyboard = await get_pagination_keyboard(
        subject = "inactive", query=serialize_timedelta(duration), next_page=pagination["next_page"],
        prev_page=pagination["prev_page"]
    )
    return ans, keyboard


async def generate_cleaning_msg(bot: Bot, chat_id: int, page: int) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    cleaning_accuracy = await check_cleaning_accuracy(chat_id)
    result = await do_cleaning(chat_id, page)

    if not result:
        return None, None
    
    users = result["users"]
    data = result["data"]
    pagination = data["pagination"]

    ans_header = f"📊 Проверка активности за {TimedeltaFormatter.format(data["сleaning_lookback"], suffix='none')}\n"
    if cleaning_accuracy: ans_header += f"<i>ℹ️ Бот в чате недавно, статистика может быть неполной.</i>\n"
    ans_header += f"📌 Норма: {data["min_messages"]} сообщ.\n📌 Макс. неактив: {TimedeltaFormatter.format(data["inactive_cutoff"], suffix='none')}\n\n"
    ans = ans_header
    ans += "<blockquote expandable>"

    for i, u in enumerate(users):
        mention = await mention_user(bot=bot, chat_id=chat_id, user_id=int(u["user_id"]))
        date = TimedeltaFormatter.format(u["last_message"]) if u["last_message"] else "никогда"
        norm = f"{u["message_count"]}/{data["min_messages"]} сообщ."

        line = f"• {mention} — {norm} | {date}\n"
        ans += line
    ans += "</blockquote>\n\n"

    keyboard = await get_pagination_keyboard(
        subject = "cleaning", query=None, next_page=pagination["next_page"],
        prev_page=pagination["prev_page"]
    )

    return ans, keyboard
