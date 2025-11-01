from aiogram import Router, F
from aiogram.types import Message

from utils.telegram.users import is_admin, mention_user, parse_user_mention
from utils.telegram.message_templates import generate_warnings_msg

from db.warnings import add_warning, remove_warning

router = Router(name="warnings")


@router.message((F.text.lower().startswith("варны")) & (F.chat.type.in_(["group", "supergroup"])))
async def get_warnings_handler(msg: Message):
    """Команда: варны @user"""
    bot = msg.bot
    target_user = None

    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user: target_user = msg.from_user

    ans = await generate_warnings_msg(bot, int(msg.chat.id), target_user)

    await msg.reply(ans, parse_mode="HTML")

@router.message(((F.text.lower().startswith("+варн")) | (F.text.lower().startswith("варн"))) & (F.chat.type.in_(["group", "supergroup"])))
async def add_warning_handler(msg: Message):
    """Команда: +варн @user [причина]"""
    bot = msg.bot
    admin_id = int(msg.from_user.id)
    chat_id = int(msg.chat.id)

    target_user = None
    text_sep = msg.text.split("\n")
    reason = text_sep[1] if len(text_sep) > 1 else None

    if len(reason or "") > 70:
        await msg.reply("❌ Слишком длинная причина варна (макс 70 символов).")
        return

    is_admin_user = await is_admin(bot, chat_id, admin_id)
    if not is_admin_user:
        await msg.reply("❌ Только администраторы могут выдавать варны.")
        return

    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user:
        await msg.reply("❌ Не удалось найти пользователя.")
        return

    warn_id = await add_warning(chat_id, int(target_user.id), admin_id, reason)
    warn_info = f" (#{warn_id})" if warn_id else ""

    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    await msg.reply(f"✅ Варн{warn_info} выдан пользователю {mention}.\nПричина: {reason or 'не указана'}", parse_mode="HTML")

    if warn_id and warn_id >= 3:
        await msg.reply(f"⚠ Пользователь {mention} получил 3 и более варнов. Рекомендуется рассмотреть возможность бана.", parse_mode="HTML")

@router.message((F.text.lower().startswith("-варн")) & (F.chat.type.in_(["group", "supergroup"])))
async def remove_warning_handler(msg: Message):
    """Команда: -варн @user INDEX"""
    bot = msg.bot
    admin_id = int(msg.from_user.id)
    chat_id = int(msg.chat.id)

    is_admin_user = await is_admin(bot, chat_id, admin_id)
    if not is_admin_user:
        await msg.reply("❌ Только администраторы могут снимать варны.")
        return

    parts = msg.text.split()
    if len(parts) >= 1:
        warn_index = None
    elif parts[2].isdigit():
        warn_index = int(parts[2]) - 1  # пользователь вводит с 1, а в коде с 0
    elif parts[1].isdigit():
        warn_index = int(parts[1]) - 1  # пользователь вводит с 1, а в коде с 0
    else:
        warn_index = None

    target_user = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user:
        await msg.reply("❌ Не удалось найти пользователя.")
        return

    success = await remove_warning(chat_id, int(target_user.id), warn_index)
    if success:
        await msg.reply(f"✅ Варн{f' #{warn_index+1}' if warn_index else ''} снят успешно.", parse_mode="HTML")
    else:
        await msg.reply("❌ Не удалось снять варн. Проверьте правильность индекса." if warn_index is not None else "❌ У пользователя нет варнов.")
