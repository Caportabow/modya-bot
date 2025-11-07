from aiogram import Router
from aiogram.types import CallbackQuery

from config import WARNINGS_PICTURE_ID, AWARDS_PICTURE_ID
from utils.telegram.users import get_chat_member_or_fall
from utils.telegram.message_templates import generate_awards_msg, generate_warnings_msg

router = Router(name="callback")

@router.callback_query()
async def callback_handler(callback: CallbackQuery):
    """Обработчик колбэков."""
    bot = callback.bot
    msg = callback.message
    ans = None

    if msg:
        parts = callback.data.split(",")
        action = parts[0]

        data = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        
        if data:
            member = await get_chat_member_or_fall(bot, int(callback.message.chat.id), data)
            if member:
                user = member.user
                
                if action == "awards":
                    answers = await generate_awards_msg(bot, int(callback.message.chat.id), user)
                    for ans in answers:
                        await callback.message.answer_photo(photo=AWARDS_PICTURE_ID, caption=ans, reply_to_message_id=callback.message.message_id, parse_mode="HTML")
                elif action == "warnings" and callback.message:
                    answers = await generate_warnings_msg(bot, int(callback.message.chat.id), user)
                    for ans in answers:
                        await callback.message.answer_photo(photo=WARNINGS_PICTURE_ID, caption=ans, reply_to_message_id=callback.message.message_id, parse_mode="HTML")

    await callback.answer()  # чтобы убрать "loading" кружок
