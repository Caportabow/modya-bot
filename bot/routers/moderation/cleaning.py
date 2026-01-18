import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from datetime import timedelta

from services.messages.cleaning import generate_minmsg_msg, generate_inactive_msg, generate_cleaning_msg

from utils.telegram.keyboards import Pagination, deserialize_timedelta
from utils.time import DurationParser
from db.chats.cleaning import check_cleanability

router = Router(name="cleaning")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(
    F.text.regexp(r"^норма(?:\s|$)", flags=re.IGNORECASE)
)
async def minmsg_handler(msg: Message):
    """Команда: норма {кол-во сообщений}"""
    parts = msg.text.split()
    if len(parts) > 1:
        msg_count = parts[1]
        if not msg_count.isdigit():
            # команда вероятно сработала случайно, останавливаем обработку
            return
        
        elif int(msg_count) <= 0:
            await msg.reply("❌ Укажите корректное число сообщений.")
            return
        msg_count = int(msg_count)
    else:
        await msg.reply("❌ Укажите минимальное количество сообщений (норму).")
        return
    
    text, keyboard = text, keyboard = await generate_minmsg_msg(msg.bot, int(msg.chat.id), 1, msg_count)

    if not text:
        await msg.reply(f"✅ Все участники успешно набрали норму!")
        return
    
    else:
        await msg.reply(text, parse_mode="HTML", reply_markup=keyboard)

@router.message(
    F.text.regexp(r"^неактив(?:\s|$)", flags=re.IGNORECASE)
)
async def inactive_handler(msg: Message):
    """Команда: неактив {период}"""
    parts = msg.text.split(maxsplit=1)

    if len(parts) > 1:
        duration = DurationParser.parse(parts[1].strip())
        if not duration:
            # команда вероятно сработала случайно, останавливаем обработку
            return
    else:
        duration = timedelta(days=1)
    
    text, keyboard = await generate_inactive_msg(msg.bot, chat_id=int(msg.chat.id), page=1, duration=duration)
    if not text:
        await msg.reply(f"✅ Все участники активны!")
        return
    
    await msg.reply(text, parse_mode="HTML", reply_markup=keyboard)

@router.message(
    F.text.lower().startswith("чистка")
)
async def cleaning_handler(msg: Message):
    """Команда: чистка"""
    chat_id = int(msg.chat.id)
    ability = await check_cleanability(chat_id)
    if not ability:
        await msg.reply("❗️ Чистка недоступна. Настройки чистки отсутствуют или заполнены не полностью.", parse_mode="HTML")
        return
    
    text, keyboard = await generate_cleaning_msg(msg.bot, chat_id, 1)

    if not text:
        await msg.reply(f"✅ Все участники прошли чистку!", parse_mode="HTML")
        return

    await msg.reply(text=text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(Pagination.filter(F.subject == "minmsg"))
async def minmsg_pagination_handler(callback: CallbackQuery, callback_data: Pagination):
    text, keyboard = await generate_minmsg_msg(callback.bot, callback.message.chat.id, callback_data.page, callback_data.query)

    if text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    
    else:
        await callback.answer(text="❌ Неизвестная ошибка.", show_alert=True)

@router.callback_query(Pagination.filter(F.subject == "inactive"))
async def inactive_pagination_handler(callback: CallbackQuery, callback_data: Pagination):
    text, keyboard = await generate_inactive_msg(callback.bot, callback.message.chat.id, callback_data.page, deserialize_timedelta(callback_data.query))

    if text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    
    else:
        await callback.answer(text="❌ Неизвестная ошибка.", show_alert=True)

@router.callback_query(Pagination.filter(F.subject == "cleaning"))
async def cleaning_pagination_handler(callback: CallbackQuery, callback_data: Pagination):
    text, keyboard = await generate_cleaning_msg(callback.bot, callback.message.chat.id, callback_data.page)

    if text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    
    else:
        await callback.answer(text="❌ Неизвестная ошибка.", show_alert=True)
