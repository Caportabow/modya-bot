from aiogram import Router, F
from aiogram.types import ChatMemberUpdated, Message

from utils.telegram.message_templates import send_welcome_message
from services.messaging.marriages import delete_marriage_and_notify
from db.users import upsert_user, remove_user
from db.chats import add_chat, forget_chat

router = Router(name="chat_member")


@router.my_chat_member()
async def on_my_chat_member(update: ChatMemberUpdated):
    """Реагируем на изменения статуса бота в чате."""
    bot = update.bot
    cid = (int(update.chat.id))

    # Если в чат добавили именно бота
    if update.new_chat_member.status in ("administrator", "member"):
        # Добавляем чат в ДБ
        await add_chat(cid)

        # Приветственное сообщение
        await send_welcome_message(bot, cid)
    
    # Если бота кикнули
    elif update.new_chat_member.status in ("left", "kicked"):
        # Удаляем чат из ДБ
        await forget_chat(cid)

@router.message(F.new_chat_members)
async def on_user_joined(msg: Message):
    cid = (int(msg.chat.id))
    for user in msg.new_chat_members:
        if not user.is_bot:
            await upsert_user(cid, user.id, user.first_name, user.username)

@router.message(F.left_chat_member)
async def on_user_left(msg: Message):
    user = msg.left_chat_member
    if user.is_bot: return
    cid = (int(msg.chat.id))
    uid = int(user.id)

    text = await delete_marriage_and_notify(msg.bot, chat_id=int(msg.chat.id), user_id=int(user.id))
    if text:
        await msg.reply(text, parse_mode="HTML")
    
    await remove_user(cid, uid)
    
    