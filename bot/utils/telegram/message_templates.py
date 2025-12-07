import random
from aiogram import Bot
from aiogram.types import User

from datetime import datetime, timezone, timedelta

from config import HELLO_PICTURE_ID, MAX_MESSAGE_LENGTH

from db.marriages import get_user_marriage, delete_marriage

from db.warnings import get_user_warnings
from db.awards import get_awards

from .users import mention_user, mention_user_with_delay
from utils.time import get_duration, format_timedelta
from db.users.rests import set_rest


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
        return [f"❕У пользователя {mention} нет наград."]

    answers = [] # список для сообщений

    ans_header = f"🏆 Награды пользователя {mention}:\n\n"
    ans = ans_header
    for i, a in enumerate(awards):
        award = a["award"]
        date = format_timedelta(datetime.now(timezone.utc) - a["assignment_date"])

        line = (
            f"🎗 Награда #{i+1}\n"
            f"• Название: {award}\n"
            f"• Выдана: {date}\n\n"
        )

        # если добавление строки превысит лимит — отправляем текущее сообщение и начинаем новое
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            answers.append(ans)
            ans = ans_header  # сбрасываем накопленное сообщение

        ans += line
    
    # добавляем остаток, если есть
    if ans.strip(): answers.append(ans)

    return answers

async def generate_warnings_msg(bot: Bot, chat_id: int, target_user):
    """Генерируем сообщение с предупреждениями пользователя."""
    warnings = await get_user_warnings(chat_id, int(target_user.id))
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)

    if not warnings:
        return [f"❕У пользователя {mention} нет варнов."]

    answers = [] # список для сообщений

    ans_header = f"⚠️ Варны пользователя {mention}:\n\n"
    ans = ans_header
    for i, w in enumerate(warnings):
        reason = w["reason"] or "Причина не указана"
        date = format_timedelta(datetime.now(timezone.utc) - w["assignment_date"])
        moderator_mention = await mention_user_with_delay(bot=bot, chat_id=chat_id, user_id=w["administrator_user_id"])
        formatted_expire_date = format_timedelta(w["expire_date"] - datetime.now(timezone.utc), False) if w["expire_date"] else "навсегда"
        line = f"┌ <b>Варн #{i+1}</b>\n├ Срок: {formatted_expire_date}\n├ Причина: {reason}\n├ Модератор: {moderator_mention}\n└ Выдан: {date}\n\n"

        # если добавление строки превысит лимит — отправляем текущее сообщение и начинаем новое
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            answers.append(ans)
            ans = ans_header  # сбрасываем накопленное сообщение

        ans += line
    
    # добавляем остаток, если есть
    if ans.strip(): answers.append(ans)

    return answers

async def generate_rest_msg(bot: Bot, chat_id: int,
                            data: str, trigger_user: User, target_user: User):
    trigger_user_mention = await mention_user(bot=bot, user_entity=trigger_user)
    target_user_mention = await mention_user(bot=bot, user_entity=target_user)
    
    if data == 'decline':
        return f"❗️Пользователю {target_user_mention} отказано в ресте.\n\nАдмин: {trigger_user_mention}"
    
    # Определяем временной диапазон
    duration = get_duration(data)

    if duration is None:
        return "❌ Не удалось распознать период."
    
    if isinstance(duration, str):
        return "❌ Вы не можете выдать рест навсегда."
    
    if duration < timedelta(days=1):
        return "❌ Вы не можете выдать рест на период меньше одной добы."

    until = datetime.now(timezone.utc) + duration
    beauty_until = format_timedelta(duration, adder=False)

    await set_rest(chat_id, int(target_user.id), until)

    return f"⏰ Пользователю {target_user_mention} успешно выдан рест на {beauty_until}\n\nАдмин: {trigger_user_mention}"

async def check_marriage_loyality(bot: Bot, chat_id: int, trigger_user_id: int, target_user_id: int) -> bool:
    """Проверяем чтобы человек был не в браке."""
    marriage = await get_user_marriage(chat_id, trigger_user_id)

    if marriage:
        partner = int(marriage["participants"][1]) if int(marriage["participants"][0]) == trigger_user_id else int(marriage["participants"][0])

        if partner == target_user_id:
            await bot.send_message(chat_id=chat_id, text=f"❌ Вы уже в браке.", parse_mode="HTML")
        else:
            partner_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=partner)
            random_phrases = ["потяните сильнее за поводок пожалуйста",
                              "Error 404: верность не найдена",
                              "ваше уплыло", "ваш партнёр сбежал, заберите пожалуйста"]
            await bot.send_message(chat_id=chat_id, text=f"❗️ {partner_mention}, {random.choice(random_phrases)}!", parse_mode="HTML")
        
        return False
    return True

async def delete_marriage_and_notify(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Удаляет брак пользователя."""
    users = await delete_marriage(chat_id, user_id) # Удаляем брак пользователя, если был

    if users:  # Пользователь был в браке
        # Отправляем сообщение оставшемуся супругу
        partner_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=users['partner'])
        await bot.send_message(chat_id, text=f"💔 {partner_mention}, мне очень жаль. Ваш брак распался", parse_mode="HTML")
        
        # Уведомляем всех детей одним сообщением
        if users['abandoned_children']:
            child_mentions = []
            for child_id in users['abandoned_children']:
                mention = await mention_user(bot=bot, chat_id=chat_id, user_id=child_id)
                child_mentions.append(mention)
            
            children_text = ", ".join(child_mentions)
            await bot.send_message(
                chat_id,
                text=f"🥀 {children_text}, увы, родители развелись и бросили вас.\nТеперь вы в детдоме.",
                parse_mode="HTML"
            )

        return True
    else: return False
