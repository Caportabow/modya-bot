import re
from aiogram import Router, F
from aiogram.types import Message

from datetime import datetime, timezone, timedelta

from utils.telegram.users import mention_user_with_delay
from utils.time import DurationParser, TimedeltaFormatter
from db.chats.cleaning import minmsg_users, verify_cleaning_possibility, inactive_users

from config import MAX_MESSAGE_LENGTH

router = Router(name="cleaning")

@router.message(
    (F.text.regexp(r"^норма(?:\s|$)", flags=re.IGNORECASE)) & 
    (F.chat.type.in_(["group", "supergroup"]))
)
async def minmsg_handler(msg: Message):
    """Команда: норма {кол-во сообщений}"""
    bot = msg.bot
    parts = msg.text.split()
    chat_id = int(msg.chat.id)
    if len(parts) > 1:
        msg_count = parts[1]
        if not msg_count.isdigit() or int(msg_count) <= 0:
            await msg.reply("❌ Укажите корректное число сообщений.")
            return
        msg_count = int(msg_count)
    else:
        await msg.reply("❌ Укажите минимальное количество сообщений (норму).")
        return
    
    possibility = await verify_cleaning_possibility(chat_id)
    if not possibility:
        await msg.reply("❌ Бот должен находиться в чате минимум неделю, прежде чем сможет проводить чистку.")
        return

    users = await minmsg_users(chat_id, msg_count)

    if not users or len(users) == 0:
        await msg.reply(f"✅ Все участники успешно набрали норму!")
        return

    ans_header = f"⚠️ Не набрали норму ({msg_count} соо.):\n\n"
    ans = ans_header
    ans += "<blockquote expandable>"

    for i, u in enumerate(users):
        mention = await mention_user_with_delay(bot=bot, chat_id=int(msg.chat.id), user_id=int(u["user_id"]))
        
        percentage = (u['count'] / msg_count) * 100
        line = f"▫️ {mention}: {u['count']} ({percentage:.0f}%)\n"
        
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            ans += "</blockquote>"
            await msg.reply(ans, parse_mode="HTML")
            ans = "<blockquote expandable>"
        ans += line

    # отправляем остаток, если есть
    if ans.strip():
        ans += "</blockquote>"
        await msg.reply(ans, parse_mode="HTML")

@router.message(
    (F.text.regexp(r"^неактив(?:\s|$)", flags=re.IGNORECASE)) & 
    (F.chat.type.in_(["group", "supergroup"]))
)
async def inactive_handler(msg: Message):
    """Команда: неактив {период}"""
    bot = msg.bot
    parts = msg.text.split()
    chat_id = int(msg.chat.id)
    if len(parts) > 1:
        duration = DurationParser.parse(" ".join(parts[1:]))
        if not duration or not isinstance(duration, timedelta):
            await msg.reply("❌ Укажите период корректно.")
            return
    else:
        duration = timedelta(days=4)
    
    possibility = await verify_cleaning_possibility(chat_id)
    if not possibility:
        await msg.reply("❌ Бот должен находиться в чате минимум неделю, прежде чем сможет проводить чистку.")
        return

    users = await inactive_users(chat_id, duration)

    if not users or len(users) == 0:
        await msg.reply(f"✅ Все участники акивны!")
        return

    now = datetime.now(timezone.utc)
    ans_header = f"💤 Неактивны последние {TimedeltaFormatter.format(duration, suffix='none')}:\n\n"
    ans = ans_header

    for i, u in enumerate(users):
        mention = await mention_user_with_delay(bot=bot, chat_id=int(msg.chat.id), user_id=int(u["user_id"]))

        date = TimedeltaFormatter.format(now - u["last_message_date"], suffix="none") if u["last_message_date"] else "никогда"
        line = f"▫️ {mention}: уже {date}\n"
        
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            await msg.reply(ans, parse_mode="HTML")
            ans = ""
        ans += line

    # отправляем остаток, если есть
    if ans.strip():
        await msg.reply(ans, parse_mode="HTML")
