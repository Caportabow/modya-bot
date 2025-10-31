from aiogram import Bot

from datetime import datetime

from config import HELLO_PICTURE_ID
from db import get_awards, get_warnings
from .users import mention_user
from utils.time import format_timedelta


async def send_welcome_message(bot: Bot, chat_id: int, private_msg: bool = False):
    """Отправляем приветственное сообщение в чат."""
    pre_text = "Привет! Спасибо, что добавили меня!\n\n"

    text = (pre_text if not private_msg else "") + '⚙️ С полным списком моих команд можно ознакомится в <a href="https://teletype.in/@caportabow/ModyaTheBot">этом списке</a>.'
    await bot.send_photo(photo=HELLO_PICTURE_ID, caption=text, chat_id=chat_id, parse_mode="HTML")

async def generate_awards_msg(bot: Bot, chat_id: int, target_user):
    """Генерируем сообщение с наградами пользователя."""
    awards = await get_awards(chat_id, int(target_user.id))
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)

    if not awards:
        return f"❕У пользователя {mention} нет наград."

    ans = f"🏆 Награды пользователя {mention}:\n\n"
    for i, w in enumerate(awards):
        award = w["award"]
        date = format_timedelta(datetime.now() - datetime.fromtimestamp(w["assigment_date"]))
        ans += f"🎗{i+1}. {award} | {date}\n\n"
    
    return ans

async def generate_warnings_msg(bot: Bot, chat_id: int, target_user):
    """Генерируем сообщение с предупреждениями пользователя."""
    warnings = await get_warnings(chat_id, int(target_user.id))
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)

    if not warnings:
        return f"❕У пользователя {mention} нет варнов."

    ans = f"⚠ Варны пользователя {mention}:\n\n"
    for i, w in enumerate(warnings):
        reason = w["reason"] or "Причина не указана"
        date = format_timedelta(datetime.now() - datetime.fromtimestamp(w["assigment_date"]))
        moderator_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=w["administrator_user_id"])
        ans += f"🔸{i+1}. {reason} | {date}\n      Модератор: {moderator_mention}\n\n"
    
    return ans
