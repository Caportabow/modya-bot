import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from middlewares.maintenance import MaintenanceMiddleware
from services.telegram.chat_member import get_chat_member
from services.telegram.user_parser import parse_user_mention
from services.messaging.user_info import generate_user_info_msg
from services.telegram.keyboards.pagination import Pagination

router = Router(name="user_info")
router.message.middleware(MaintenanceMiddleware())
router.callback_query.middleware(MaintenanceMiddleware())
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(
    F.text.regexp(r"^(кто я|кто ты)(\s+@?\S+)?$", flags=re.IGNORECASE)
)
async def user_info_handler(msg: Message):
    """Команда: кто [я|ты]"""
    bot = msg.bot
    m = re.match(r"^(кто)\s+(я|ты)(?:\s+(.*))?$", msg.text.lower())
    if not m: return

    target = m.group(2)
    if target == "я":
        user = msg.from_user
    elif target == "ты":
        if msg.reply_to_message:
            user = msg.reply_to_message.from_user
        else:
            user = await parse_user_mention(bot, msg)
            if not user:
                await msg.reply("❌ Укажи пользователя реплаем или упоминанием.")
                return

    if user.is_bot:
        await msg.reply("❌ Эта команда не поддерживает ботов.")
        return
    
    chat_id = int(msg.chat.id)
    text, keyboard, img = await generate_user_info_msg(bot, chat_id, user)

    if not text:
        await msg.reply("❌ Нет данных по этому пользователю.")
        return
    
    await bot.send_photo(chat_id=chat_id,
        photo=img,
        caption=text, reply_to_message_id=msg.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(
    Pagination.filter(
        F.subject.in_({"user_warnings", "user_awards", "family"}) & (F.is_back_button == True)
    )
)
async def user_info_back_pagination_handler(callback: CallbackQuery, callback_data: Pagination):
    bot = callback.bot
    msg = callback.message
    chat_id = int(callback.message.chat.id)
    member = await get_chat_member(bot = bot, chat_id = chat_id, user_id = callback_data.query)
    if not member: return

    text, keyboard, img = await generate_user_info_msg(callback.bot, callback.message.chat.id, member.user)
    if text:
        await msg.edit_media(
            media=InputMediaPhoto(
                media=img,
                caption=text,
                parse_mode="HTML"
            ), 
            reply_markup=keyboard
        )
        await callback.answer("") # пустой ответ, чтобы убрать "часики"
    
    else:
        await callback.answer(text="❌ Неизвестная ошибка.", show_alert=True)
