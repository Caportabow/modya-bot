from aiogram import Router
from aiogram.types import CallbackQuery

from config import WARNINGS_PICTURE_ID, AWARDS_PICTURE_ID
from utils.telegram.users import get_chat_member_or_fall, is_admin, mention_user
from utils.telegram.message_templates import generate_awards_msg, generate_warnings_msg, generate_rest_msg

router = Router(name="callback")

@router.callback_query()
async def callback_handler(callback: CallbackQuery):
    """Обработчик колбэков."""
    bot = callback.bot
    msg = callback.message

    if msg:
        parts = callback.data.split(",")
        action = parts[0]

        if action == 'rest':
            if len(parts) > 1:
                data = parts[1]
                trigger_user = callback.from_user
                target_user = msg.reply_to_message.from_user

                admin = await is_admin(bot, int(msg.chat.id), int(trigger_user.id))
                if not admin:
                    await msg.answer(text="❌ Вы должны быть админом, чтобы выдать рест.", parse_mode="HTML")
                    return

                ans = await generate_rest_msg(bot, int(msg.chat.id),
                                data, trigger_user, target_user)
                
                await msg.edit_reply_markup()
                await msg.answer(text=ans, parse_mode="HTML")

        user_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        
        if user_id:
            member = await get_chat_member_or_fall(bot, int(msg.chat.id), user_id)
            if member:
                user = member.user
                
                if action == "awards":
                    answers = await generate_awards_msg(bot, int(msg.chat.id), user)
                    for ans in answers:
                        await msg.answer_photo(photo=AWARDS_PICTURE_ID, caption=ans, reply_to_message_id=callback.message.message_id, parse_mode="HTML")
                elif action == "warnings":
                    answers = await generate_warnings_msg(bot, int(msg.chat.id), user)
                    for ans in answers:
                        await msg.answer_photo(photo=WARNINGS_PICTURE_ID, caption=ans, reply_to_message_id=callback.message.message_id, parse_mode="HTML")

    await callback.answer()  # чтобы убрать "loading" кружок
