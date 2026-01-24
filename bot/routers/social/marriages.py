import re
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from middlewares.maintenance import MaintenanceMiddleware
from services.messaging.marriages import generate_all_marriages_msg, can_get_married, delete_marriage_and_notify
from services.telegram.user_mention import mention_user
from services.telegram.user_parser import parse_user_mention
from services.telegram.keyboards.pagination import Pagination
from services.telegram.keyboards.marriages import MarriageRequest, get_marriage_request_keyboard

from services.time_utils import TimedeltaFormatter

from config import MARRIAGES_PICTURE_ID
from db.marriages import get_user_marriage, make_marriage

router = Router(name="marriages")
router.message.middleware(MaintenanceMiddleware())
router.callback_query.middleware(MaintenanceMiddleware())
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(
    F.text.lower() == "браки"
)
async def all_marriages_handler(msg: Message):
    """Команда: браки"""
    bot = msg.bot
    chat_id = int(msg.chat.id)  
    
    text, keyboard = await generate_all_marriages_msg(bot, chat_id, page=1)
    if not text:
        await msg.reply("❌ В этом чате нет браков.")
        return
    
    await msg.reply_photo(photo=MARRIAGES_PICTURE_ID, caption=text, parse_mode="HTML", reply_markup=keyboard)

@router.message(
    F.text.lower() == "мой брак"
)
async def my_marriage_handler(msg: Message):
    """Команда: мой брак"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    user_id = int(msg.from_user.id)
    
    marriage = await get_user_marriage(chat_id, user_id)
    if not marriage:
        await msg.reply("❌ Вы не женаты.")
        return
    
    mention_1 = await mention_user(bot=bot, chat_id=chat_id, user_id=int(marriage["participants"][0]))
    mention_2 = await mention_user(bot=bot, chat_id=chat_id, user_id=int(marriage["participants"][1]))
    now = datetime.now(timezone.utc)
    duration = TimedeltaFormatter.format(now-marriage["date"], suffix="none")

    ans = f"👰👨‍⚖️ Брак между {mention_1} и {mention_2}:\n\n"
    ans += f"🗓 Зарегистрирован {marriage["date"]:%d.%m.%Y}\n"
    ans += f"⌛ Длится уже {duration}\n"

    await msg.reply_photo(photo=MARRIAGES_PICTURE_ID, caption=ans, parse_mode="HTML")

@router.message(
    F.text.regexp(r"^брак(?:\s|$)", flags=re.IGNORECASE)
)
async def propose(msg: Message):
    """Команда: брак {упоминание}"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    trigger_user_id = int(msg.from_user.id)
    target_user = await parse_user_mention(bot, msg)

    if msg.reply_to_message and not target_user:
        target_user = msg.reply_to_message.from_user
    
    if not target_user:
        await msg.reply("❌ Укажите пользователя, которому хотите сделать предложение.")
        return
    target_user_id = int(target_user.id)

    if target_user.is_bot:
        await msg.reply("❌ Вы не можете поженится с ботом.")
        return

    if target_user_id == trigger_user_id:
        await msg.reply("❌ Вы не можете жениться на самом себе.")
        return
    
    ok, text = await can_get_married(bot, chat_id, trigger_user_id, target_user_id)
    if not ok:
        await msg.reply(text, parse_mode="HTML")
        return

    keyboard = await get_marriage_request_keyboard(trigger_user_id, target_user_id)

    target_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    trigger_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=msg.from_user)

    ans = f"🎊 {target_user_mention}, вас приглашают к алтарю!\n"
    ans += f"💞 {trigger_user_mention} просит вашей руки и сердца.\n"
    ans += f"💫 Согласны ли вы стать парой?"

    await msg.reply_photo(
        photo=MARRIAGES_PICTURE_ID, caption=ans,
        reply_markup=keyboard, parse_mode="HTML"
    )

@router.message(
    F.text.lower() == "развод"
)
async def divorce(msg: Message):
    """Команда: развод"""
    text = await delete_marriage_and_notify(msg.bot, chat_id=int(msg.chat.id), user_id=int(msg.from_user.id))
    if text:
        await msg.reply(text, parse_mode="HTML")

@router.callback_query(MarriageRequest.filter(F.response == "accept"))
async def marriage_accept_callback_handler(callback: CallbackQuery, callback_data: MarriageRequest):
    """Обрабатывает согласие на предложение о браке."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return

    chat_id = int(msg.chat.id)
    trigger_id = int(callback.from_user.id)
    first_partner = callback_data.trigger_user_id
    second_partner = callback_data.target_user_id

    # Проверка прав доступа
    if trigger_id != second_partner:
        await callback.answer(text="❌ Вы не можете ответить на чужое предложение.", show_alert=True)
        return

    await msg.edit_reply_markup()
    trigger_user = await mention_user(bot=bot, chat_id=chat_id, user_id=first_partner)
    target_user = await mention_user(bot=bot, chat_id=chat_id, user_id=second_partner)

    ok, text = await can_get_married(bot, chat_id, first_partner, second_partner)
    if not ok:
        await msg.edit_caption(text, parse_mode="HTML")
        return

    await make_marriage(chat_id, [first_partner, second_partner])
    
    ans = f"💍 Поздравляем молодоженов!\n💝 С сегодняшнего дня {trigger_user} и {target_user} женаты!"

    await msg.edit_caption(caption=ans, parse_mode="HTML")
    await callback.answer("") # пустой ответ, чтобы убрать "часики"

@router.callback_query(MarriageRequest.filter(F.response == "decline"))
async def marriage_decline_callback_handler(callback: CallbackQuery, callback_data: MarriageRequest):
    """Обрабатывает отказ от предложения брака."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return

    chat_id = int(msg.chat.id)

    # Проверка прав доступа
    if int(callback.from_user.id) != callback_data.target_user_id:
        await callback.answer(text="❌ Вы не можете ответить на чужое предложение.", show_alert=True)
        return

    await msg.edit_reply_markup()
    trigger_user = await mention_user(bot=bot, chat_id=chat_id, user_id=callback_data.trigger_user_id)
    target_user = await mention_user(bot=bot, chat_id=chat_id, user_id=callback_data.target_user_id) 
    
    ans = f"💔 {trigger_user}, мне очень жаль..\n🥀 {target_user} отказался(-ась) от вашего предложения."
    await msg.edit_caption(caption=ans, parse_mode="HTML")
    await callback.answer("") # пустой ответ, чтобы убрать "часики"

@router.callback_query(MarriageRequest.filter(F.response == "retire"))
async def marriage_retire_callback_handler(callback: CallbackQuery, callback_data: MarriageRequest):
    """Обрабатывает побег в предложении брака."""
    msg = callback.message
    if not msg or not msg.chat: return

    # Проверка прав доступа
    if int(callback.from_user.id) != callback_data.trigger_user_id:
        await callback.answer(text="❌ Вы не можете нажать на эту кнопку.", show_alert=True)
    else:
        await msg.delete()
        await callback.answer("") # пустой ответ, чтобы убрать "часики"


@router.callback_query(Pagination.filter(F.subject == "all_marriages"))
async def all_marriages_pagination_callback_handler(callback: CallbackQuery, callback_data: Pagination):
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return
    chat_id = int(msg.chat.id)

    text, keyboard = await generate_all_marriages_msg(bot, chat_id, page=callback_data.page)
    if not text:
        await callback.answer(text="❌ Неизвестная ошибка.", show_alert=True)
        return

    await msg.edit_caption(caption=text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer("") # пустой ответ, чтобы убрать "часики"
