import asyncio

from aiogram import Router, F
from aiogram.types import ChatMemberUpdated
from telethon import TelegramClient

from utils.telegram.message_templates import send_welcome_message
from db import upsert_user, remove_user

router = Router(name="chat_member")

# --------------------
# Helper function
# --------------------
async def sync_members(telethon_client: TelegramClient, chat_id: int):
    """Синхронизируем список участников чата."""
    async for user in telethon_client.iter_participants(chat_id):
        await upsert_user(int(chat_id), int(user.id), user.username, user.first_name)
# --------------------


@router.my_chat_member()
async def on_my_chat_member(update: ChatMemberUpdated, telethon_client: TelegramClient):
    """Реагируем на изменения статуса бота в чате."""
    bot = update.bot
    cid = (int(update.chat.id))

    # Если в чат добавили именно бота
    if update.new_chat_member.status in ("administrator", "member"):
        # Приветственное сообщение
        await send_welcome_message(bot, cid)

        # Бот только что добавлен в чат → синкаем участников
        asyncio.create_task(sync_members(telethon_client, cid))

@router.chat_member()
async def on_chat_member(update: ChatMemberUpdated):
    """Реагируем на добавление бота в чат или на изменения участников."""
    user = update.from_user
    uid = int(user.id)
    cid = (int(update.chat.id))

    if update.new_chat_member.status in ("left", "kicked"):
        await remove_user(cid, uid)
    elif update.new_chat_member.status in ("member"):
        await upsert_user(cid, uid, user.username, user.first_name)
