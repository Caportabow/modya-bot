import re
from aiogram import Router, F
from aiogram.types import Message

from middlewares.maintenance import MaintenanceMiddleware
from db.users.nicknames import set_nickname

router = Router(name="nicknames")
router.message.middleware(MaintenanceMiddleware())
router.callback_query.middleware(MaintenanceMiddleware())
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(
    (F.text.regexp(r"^\+ник(?:\s|$)", flags=re.IGNORECASE))
)
async def set_nick(msg: Message):
    """Команда: +ник NICKNAME"""
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply("❌ Укажите желаемый ник")
        return
    nickname = parts[1].strip()

    if len(nickname) > 30:
        await msg.reply("❌ Слишком длинный ник (макс 30 символов)")
        return

    await set_nickname(int(msg.chat.id), int(msg.from_user.id), nickname)
    await msg.reply(f"🎭 Теперь вы известны как: {nickname}")

@router.message(
    F.text.lower() == "-ник"
)
async def unset_nick(msg: Message):
    """Команда: -ник (сброс ника)"""
    await set_nickname(int(msg.chat.id), int(msg.from_user.id), msg.from_user.first_name)
    await msg.reply(f"👤 Возвращено оригинальное имя.")
