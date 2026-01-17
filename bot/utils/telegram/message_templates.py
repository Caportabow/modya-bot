import random
from aiogram import Bot
from aiogram.types import User, Message, BufferedInputFile

from datetime import datetime, timezone

from config import HELLO_PICTURE_ID, MAX_MESSAGE_LENGTH

from db.users.rp_commands import get_user_rp_commands

from db.quotes import get_random_quote

from db.marriages import get_user_marriage, delete_marriage
from db.marriages.families import get_family_tree_data

from db.chats.settings import get_max_warns
from db.chats.cleaning import check_cleaning_accuracy

from db.warnings import get_user_warnings
from db.awards import get_awards

from utils.telegram.keyboards import get_quote_delition_keyboard
from utils.telegram.users import mention_user, mention_user_with_delay
from utils.roleplay import parse_rp_command
from utils.time import TimedeltaFormatter
from utils.web.families import make_family_tree

# TODO: Full util rework
async def send_welcome_message(bot: Bot, chat_id: int, private_msg: bool = False):
    pre_text = "👀 О, новый чат. Интересно.\n\n"

    text = (pre_text if not private_msg else "") + (
        "Я — Модя. Превращаю хаос флудов в порядок\n\n"
        "Здесь без спама и бесполезных команд:\n"
        "• 📣 Умный созыв участников\n"
        "• 📊 Управление чистками и подробная статистика\n"
        "• 🛡️ Система варнов и простая админ-панель\n"
        "• ⏸️ Полное управление рестами\n"
        "• ✨ И много других полезных функций\n\n"
        '<a href="https://teletype.in/@caportabow/ModyaTheBot">🔗 Полный список команд</a>'
    )

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
    ans += "<blockquote expandable>"

    for i, a in enumerate(awards):
        award = a["award"]
        date = TimedeltaFormatter.format(datetime.now(timezone.utc) - a["assignment_date"])

        line = (
            f"🎗 Награда #{i+1}\n"
            f"• Название: {award}\n"
            f"• Выдана: {date}\n\n"
        )

        # если добавление строки превысит лимит — отправляем текущее сообщение и начинаем новое
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            ans += "</blockquote>"
            answers.append(ans)
            ans = ans_header  # сбрасываем накопленное сообщение
            ans += "<blockquote expandable>"

        ans += line
    
    # добавляем остаток, если есть
    if ans.strip():
        ans += "</blockquote>"
        answers.append(ans)

    return answers

async def generate_warnings_msg(bot: Bot, chat_id: int, target_user):
    """Генерируем сообщение с предупреждениями пользователя."""
    warnings = await get_user_warnings(chat_id, int(target_user.id))
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)

    if not warnings:
        return [f"❕У пользователя {mention} нет варнов."]

    answers = [] # список для сообщений

    warnings_count = len(warnings)
    max_warns = await get_max_warns(int(chat_id))

    ans_header = f"⚠️ Варны пользователя {mention} ({warnings_count}/{max_warns}):\n\n"
    ans = ans_header
    ans += "<blockquote expandable>"

    for i, w in enumerate(warnings):
        reason = w["reason"] or "Причина не указана."
        date = TimedeltaFormatter.format(datetime.now(timezone.utc) - w["assignment_date"])
        moderator_mention = await mention_user_with_delay(bot=bot, chat_id=chat_id, user_id=w["administrator_user_id"])
        formatted_expire_date = TimedeltaFormatter.format(w["expire_date"] - datetime.now(timezone.utc), suffix="none") if w["expire_date"] else "навсегда"
        line = f"┌ Варн #{i+1}\n├ Срок: {formatted_expire_date}\n├ Причина: {reason}\n├ Модератор: {moderator_mention}\n└ Выдан: {date}\n\n"

        # если добавление строки превысит лимит — отправляем текущее сообщение и начинаем новое
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            ans += "</blockquote>"
            answers.append(ans)
            ans = ans_header  # сбрасываем накопленное сообщение
            ans += "<blockquote expandable>"

        ans += line
    
    # добавляем остаток, если есть
    if ans.strip():
        ans += "</blockquote>"
        answers.append(ans)

    return answers

async def describe_rest(bot: Bot, chat_id: int, target_user_entity: User, rest: dict) -> str:
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
                              "error 404: верность не найдена",
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
        await bot.send_message(chat_id, text=f"💔 {partner_mention}, ваш супруг покинул чат. Семейная жизнь окончена.", parse_mode="HTML")
        
        # Уведомляем всех детей одним сообщением
        if users['abandoned_children']:
            child_mentions = []
            for child_id in users['abandoned_children']:
                mention = await mention_user(bot=bot, chat_id=chat_id, user_id=child_id)
                child_mentions.append(mention)
            
            children_text = ", ".join(child_mentions)
            await bot.send_message(
                chat_id,
                text=f"🥀 {children_text}, один из родителей покинул семью. Вы официально осиротели.",
                parse_mode="HTML"
            )

        return True
    else: return False

async def family_tree(bot: Bot, chat_id: int, user_id: int, user_entity: User):
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=user_entity)
    family_tree_data = await get_family_tree_data(chat_id, user_id)

    if not family_tree_data or len(family_tree_data) == 0:
        await bot.send_message(chat_id=chat_id, text=f"❌ {mention} не состоит в какой-либо семье.", parse_mode="HTML")
        return
    
    family_tree_bytes = await make_family_tree(family_tree_data)

    photo = BufferedInputFile(family_tree_bytes, filename="family_tree.jpeg")
    await bot.send_photo(chat_id=chat_id, photo=photo, caption=f"🌳 Семейное древо {mention}", parse_mode="HTML")

async def process_roleplay_message(msg: Message) -> bool:
    """
    Обрабатывает ролевые сообщения.
    Возвращает True, если сообщение содержало RP команду. Иначе False.
    """
    bot = msg.bot
    user = msg.from_user
    chat = msg.chat

    # рп команды
    text = msg.text or msg.caption

    if text and user and bot:
        # Удаляем префиксы
        prefixes = ["!", "/", "-", "—", "."]
        text = text.lstrip("".join(prefixes))

        target_user_entity = None
        reply_message = msg.reply_to_message or msg
        target_user_entity = reply_message.from_user
        
        if not target_user_entity and msg.entities:
            # Пытаемся найти упоминание пользователя в тексте
            for entity in msg.entities:
                if entity.type == "text_mention" and entity.user:
                    target_user_entity = entity.user

        user_rp_commands = await get_user_rp_commands(int(chat.id), int(user.id))
        command = await parse_rp_command(
            bot, int(chat.id), text,
            user, target_user_entity, user_rp_commands
        )

        if command:
            await reply_message.reply(command, parse_mode="HTML")
            return True

    return False

async def send_random_sticker_quote(msg: Message):
    """Отправляет рандомную цитату в чат."""
    quote_sticker_id = await get_random_quote(int(msg.chat.id))

    if quote_sticker_id:
        keyboard = await get_quote_delition_keyboard()

        await msg.reply_sticker(sticker=quote_sticker_id, reply_markup=keyboard)
