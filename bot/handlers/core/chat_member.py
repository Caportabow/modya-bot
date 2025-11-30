from aiogram import Router, F
from aiogram.types import ChatMemberUpdated, Message

from utils.telegram.message_templates import send_welcome_message, delete_marriage_and_notify
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
async def on_user_joined(message: Message):
    cid = (int(message.chat.id))
    for user in message.new_chat_members:
        if not user.is_bot:
            await upsert_user(cid, user.id, user.first_name, user.username)

@router.message(F.left_chat_member)
async def on_user_left(message: Message):
    user = message.left_chat_member
    if user.is_bot: return
    cid = (int(message.chat.id))
    uid = int(user.id)

    await delete_marriage_and_notify(message.bot, cid, uid) # Удаляем брак пользователя, если был
    await remove_user(cid, uid)
    
    