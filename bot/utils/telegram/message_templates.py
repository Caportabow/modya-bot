import random
from aiogram import Bot
from aiogram.types import Message

from config import HELLO_PICTURE_ID

from db.users.rp_commands import get_user_rp_commands

from db.quotes import get_random_quote

from db.marriages import get_user_marriage, delete_marriage

from services.telegram.keyboards.quotes import get_quote_delition_keyboard
from services.telegram.user_mention import mention_user
from services.messaging.roleplay import parse_rp_command

# TODO: Full util rework
async def send_welcome_message(bot: Bot, chat_id: int, private_msg: bool = False):
    """Отправляет приветственное сообщение с описанием бота."""

    text = (
        "Я — Модя. Превращаю хаос флудов в порядок\n\n"
        "Вот что я умею:\n"
        "• 📣 Умный созыв участников\n"
        "• 📊 Управление чистками и подробная статистика\n"
        "• 🛡️ Система варнов и простая админ-панель\n"
        "• ⏸️ Полное управление рестами\n"
        "• ✨ И много других полезных функций\n\n"
        '<a href="https://teletype.in/@caportabow/ModyaTheBot">🔗 Полный список команд</a>'
    )

    await bot.send_photo(photo=HELLO_PICTURE_ID, caption=text, chat_id=chat_id, parse_mode="HTML")

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
