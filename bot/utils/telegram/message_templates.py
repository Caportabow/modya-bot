import random
from aiogram import Bot

from config import HELLO_PICTURE_ID
from db.marriages import get_user_marriage, delete_marriage
from services.telegram.user_mention import mention_user

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

async def delete_marriage_and_notify(bot: Bot, chat_id: int, user_id: int, gone_from_chat: bool) -> bool:
    """Удаляет брак пользователя."""
    users = await delete_marriage(chat_id, user_id) # Удаляем брак пользователя, если был

    if users:  # Пользователь был в браке
        # Отправляем сообщение оставшемуся супругу
        partner_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=users['partner'])
        if gone_from_chat: msg = f"💔 {partner_mention}, ваш супруг покинул чат. Семейная жизнь окончена."
        else: msg = f"💔 {partner_mention}, мне очень жаль, ваш супруг подал на развод. Семейная жизнь окончена."
        await bot.send_message(chat_id, text=msg, parse_mode="HTML")
        
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
