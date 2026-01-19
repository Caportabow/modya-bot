import re
import asyncio

from aiogram import Router, F
from aiogram.types import Message

from services.user_mention import mention_user
from services.telegram_chat_permissions import is_admin
from db.users import get_all_users_in_chat

router = Router(name="call")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(
    F.text.lower().startswith("/call") | F.text.lower().startswith("созвать") | 
    F.text.lower().startswith("созыв") | F.text.lower().startswith("собрать") |
    F.text.lower().startswith("общий созыв")
)
async def сall_members(msg: Message):
    """Команда: созвать | /call | созвать всех | собрать всех | созыв | общий созыв"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    
    arg = re.sub(
        r'^(?:/call|созвать всех|собрать всех|созвать|собрать|общий созыв)\b\s*',
        '',
        msg.text,
        flags=re.IGNORECASE
    )
    if len(arg) > 300:
        await msg.reply("❌ Слишком длинный текст для созыва (макс 300 символов).")
        return

    admin = await is_admin(bot, chat_id, int(msg.from_user.id))
    if not admin:
        await msg.reply("❌ Только администраторы могут использовать эту команду.")
        return
    
    users = await get_all_users_in_chat(chat_id)
    if not users:
        await msg.reply("❌ Нет участников для созыва.")
        return
    
    reply_msg_id = msg.reply_to_message.message_id if msg.reply_to_message else None
    
    for i in range(0, len(users), 5):
        chunk = users[i:i+5]
        text = f"⚡ {arg if arg.strip() else 'Внимание!'}\n\n"

        mentions = await asyncio.gather(*(mention_user(bot=bot, chat_id=chat_id, user_id=u) for u in chunk))
        text += "\n".join(mentions)

        if reply_msg_id:
            await bot.send_message(chat_id=chat_id, text=text, reply_to_message_id=reply_msg_id, parse_mode="HTML")
        else:
            await msg.reply(text, parse_mode="HTML")
