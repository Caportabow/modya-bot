from aiogram import Router
from aiogram.types import CallbackQuery

from utils.telegram.users import get_chat_member_or_fall
from utils.telegram.message_templates import generate_awards_msg, generate_warnings_msg

router = Router(name="callback")

@router.callback_query()
async def callback_handler(callback: CallbackQuery):
    """Обработчик колбэков."""
    bot = callback.bot
    ans = None

    if callback.message:
        parts = callback.data.split(",")
        action = parts[0]

        user_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        
        if user_id:
            member = await get_chat_member_or_fall(bot, int(callback.message.chat.id), user_id)
            if member:
                user = member.user
                
                if action == "awards":
                    ans = await generate_awards_msg(bot, int(callback.message.chat.id), user)
                elif action == "warnings" and callback.message:
                    ans = await generate_warnings_msg(bot, int(callback.message.chat.id), user)

        if ans:
            await callback.message.answer(ans, reply_to_message_id=callback.message.message_id, parse_mode="HTML")

    await callback.answer()  # чтобы убрать "loading" кружок
