import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from services.messages.awards import generate_user_awards_msg
from utils.telegram.keyboards import Pagination

from db.awards import add_award, remove_award
from config import AWARDS_PICTURE_ID
from utils.telegram.users import mention_user, parse_user_mention, get_chat_member_or_fall

router = Router(name="awards")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(
    F.text.regexp(r"^наградить(?:\s|$)", flags=re.IGNORECASE)
)
async def add_award_handler(msg: Message):
    """Команда: наградить @user [причина]"""
    bot = msg.bot
    giver_id = int(msg.from_user.id)
    chat_id = int(msg.chat.id)

    target_user = None
    text_sep = msg.text.split("\n")
    award = text_sep[1] if len(text_sep) > 1 else None
    if not award:
        await msg.reply("❌ Укажите награду пользователя.")
        return
    
    if len(award) > 80:
        await msg.reply("❌ Слишком длинная награда (макс 80 символов).")
        return

    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user:
        await msg.reply("❌ Не удалось найти пользователя.")
        return
    
    if giver_id == int(target_user.id):
        await msg.reply("❌ Нельзя награждать самого себя.")
        return

    await add_award(chat_id, int(target_user.id), giver_id, award)
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    await msg.reply(f"🎖️ Награда \"{award}\" вручена пользователю {mention}", parse_mode="HTML")

@router.message(
    F.text.regexp(r"^награды(?:\s|$)", flags=re.IGNORECASE)
)
async def get_awards_handler(msg: Message):
    """Команда: награды @user"""
    bot = msg.bot
    target_user = None
    chat_id = int(msg.chat.id)

    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user: target_user = msg.from_user

    text, keyboard = await generate_user_awards_msg(bot, chat_id, target_user, 1)
    if not text:
        mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
        await msg.reply(f"❕У пользователя {mention} нет наград.", parse_mode="HTML")
        return

    await msg.reply_photo(photo=AWARDS_PICTURE_ID, caption=text, parse_mode="HTML", reply_markup=keyboard)

@router.message(
    F.text.regexp(r"^снять награду(?:\s|$)", flags=re.IGNORECASE)
)
async def remove_award_handler(msg: Message):
    """Команда: -награда INDEX"""
    target_id = int(msg.from_user.id)
    chat_id = int(msg.chat.id)

    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        award_index = None
    else: 
        award_index = int(parts[1]) - 1  # пользователь вводит с 1, а в коде с 0

    success = await remove_award(chat_id, target_id, award_index)
    if success:
        await msg.reply(f"✅ Награда{f' #{award_index+1}' if award_index else ''} снята успешно.", parse_mode="HTML")
    else:
        await msg.reply("❌ Не удалось снять награду. Проверьте правильность индекса." if award_index is not None else "❌ У вас нет наград.")

@router.callback_query(Pagination.filter((F.subject == "user_awards") & F.is_back_button == False))
async def user_awards_pagination_handler(callback: CallbackQuery, callback_data: Pagination):
    bot = callback.bot
    chat_id = int(callback.message.chat.id)
    member = await get_chat_member_or_fall(bot = bot, chat_id = chat_id, user_id = callback_data.query)
    if not member: return

    text, keyboard = await generate_user_awards_msg(callback.bot, callback.message.chat.id, member.user, callback_data.page, callback_data.with_back_button)
    if text:
        await callback.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=keyboard)
    
    else:
        await callback.answer(text="❌ Неизвестная ошибка.", show_alert=True)
