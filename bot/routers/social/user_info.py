import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from config import AWARDS_PICTURE_ID, WARNINGS_PICTURE_ID

from services.messages.warnings import generate_user_warnings_msg
from services.messages.awards import generate_user_awards_msg
from services.messages.family import generate_family_tree_msg
from services.messages.user_info import generate_user_info_msg

from utils.telegram.keyboards import UserInfo, Pagination
from utils.telegram.users import parse_user_mention, get_chat_member_or_fall

router = Router(name="user_info")
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
    UserInfo.filter(F.secondary_action == "family")
)
async def user_family_info_callback_handler(callback: CallbackQuery, callback_data: UserInfo):
    """Обрабатывает запрос об семье пользователя."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return
    user_info = callback_data
    chat_id = int(msg.chat.id)
    user_id = user_info.user_id

    member = await get_chat_member_or_fall(bot = bot, chat_id = chat_id, user_id = user_id)
    if not member:
        return

    text, keyboard, img = await generate_family_tree_msg(bot, chat_id, member.user, True)
    if not text:
        if user_id == int(callback.from_user.id):
            await callback.answer(text=f"❕Вы пока не состоите в семье.", show_alert=True)
        else:
            await callback.answer(text=f"❕Этот пользователь пока не состоит в семье.", show_alert=True)
        return

    await msg.edit_media(
        media=InputMediaPhoto(
            media=img,
            caption=text,
            parse_mode="HTML"
        ), 
        reply_markup=keyboard
    )

@router.callback_query(
    UserInfo.filter(F.secondary_action == "awards")
)
async def user_awards_info_callback_handler(callback: CallbackQuery, callback_data: UserInfo):
    """Обрабатывает запросы об наградах пользователя."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return
    user_info = callback_data
    chat_id = int(msg.chat.id)
    user_id = user_info.user_id

    member = await get_chat_member_or_fall(bot = bot, chat_id = chat_id, user_id = user_id)
    if not member:
        return

    text, keyboard = await generate_user_awards_msg(bot, chat_id, member.user, 1, True)
    if not text:
        if user_id == int(callback.from_user.id):
            await callback.answer(text=f"❕У вас нет наград.", show_alert=True)
        else:
            await callback.answer(text=f"❕У этого пользователя нет наград.", show_alert=True)
        return

    await msg.edit_media(
        media=InputMediaPhoto(
            media=AWARDS_PICTURE_ID,
            caption=text,
            parse_mode="HTML"
        ), 
        reply_markup=keyboard
    )

@router.callback_query(
    UserInfo.filter(F.secondary_action == "warnings")
)
async def user_warnings_info_callback_handler(callback: CallbackQuery, callback_data: UserInfo):
    """Обрабатывает запросы об предупрежденях пользователя."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return
    user_info = callback_data
    chat_id = int(msg.chat.id)
    user_id = user_info.user_id

    member = await get_chat_member_or_fall(bot = bot, chat_id = chat_id, user_id = user_id)
    if not member:
        return

    text, keyboard = await generate_user_warnings_msg(bot, chat_id, member.user, 1, True)
    if not text:
        if user_id == int(callback.from_user.id):
            await callback.answer(text=f"❕У вас нет предупреждений.", show_alert=True)
        else:
            await callback.answer(text=f"❕У этого пользователя нет предупреждений.", show_alert=True)
        return

    await msg.edit_media(
        media=InputMediaPhoto(
            media=WARNINGS_PICTURE_ID,
            caption=text,
            parse_mode="HTML"
        ), 
        reply_markup=keyboard
    )


@router.callback_query(
    Pagination.filter(
        F.subject.in_({"user_warnings", "user_awards", "family"}) & F.is_back_button
    )
)
async def user_info_back_pagination_handler(callback: CallbackQuery, callback_data: Pagination):
    bot = callback.bot
    msg = callback.message
    chat_id = int(callback.message.chat.id)
    member = await get_chat_member_or_fall(bot = bot, chat_id = chat_id, user_id = callback_data.query)
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
    
    else:
        await callback.answer(text="❌ Неизвестная ошибка.", show_alert=True)
