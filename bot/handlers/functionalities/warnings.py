import re
from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime, timezone, timedelta

from config import WARNINGS_PICTURE_ID, MAX_MESSAGE_LENGTH
from utils.telegram import remove_message_entities
from utils.time import DurationParser, TimedeltaFormatter
from utils.telegram.users import is_admin, is_creator, mention_user, parse_user_mention, mention_user_with_delay
from utils.telegram.message_templates import generate_warnings_msg

from db.chats.settings import get_max_warns
from db.warnings import add_warning, remove_warning, get_all_warnings, amnesty

router = Router(name="warnings")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(
    F.text.lower().startswith("все варны")
)
async def stats_handler(msg: Message):
    """Команда: все варны"""
    bot = msg.bot

    users_with_warnings = await get_all_warnings(int(msg.chat.id))
    if not users_with_warnings or len(users_with_warnings) == 0:
        await msg.reply("❌ У пользователей этого чата нет варнов.")
        return
    
    ans_header = f"📛 Список предупреждений:\n\n"
    ans = ans_header
    ans += "<blockquote expandable>"

    for i, u in enumerate(users_with_warnings):
        mention = await mention_user_with_delay(bot=bot, chat_id=int(msg.chat.id), user_id=int(u["user_id"]))
        
        max_warns = await get_max_warns(int(msg.chat.id))
        line = f"▫️ {mention} - {u['count']}/{max_warns}\n"
        
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            ans += "</blockquote>"
            await msg.reply(ans, parse_mode="HTML")
            ans = ans_header  # сбрасываем накопленное сообщение
            ans += "<blockquote expandable>"
        
        ans += line
    
    # отправляем остаток, если есть
    if ans.strip():
        await msg.reply(ans, parse_mode="HTML")

@router.message(
    F.text.lower().startswith("варны")
)
async def get_user_warnings_handler(msg: Message):
    """Команда: варны @user"""
    bot = msg.bot
    target_user = None

    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user: target_user = msg.from_user

    if target_user.is_bot:
        await msg.reply("❌ Вы не можете просмотреть варны бота.")
        return

    answers = await generate_warnings_msg(bot, int(msg.chat.id), target_user)

    for ans in answers:
        await msg.reply_photo(photo=WARNINGS_PICTURE_ID, caption=ans, parse_mode="HTML")

@router.message(
    F.text.regexp(r"^\+варн(?:\s|$)", flags=re.IGNORECASE)
)
async def add_warning_handler(msg: Message):
    """Команда: +варн {период} @user {отступ} {причина}"""
    bot = msg.bot
    admin_id = int(msg.from_user.id)
    chat_id = int(msg.chat.id)

    target_user = None
    text_sep = msg.text.split("\n")

    no_entities_text = remove_message_entities(msg, text_sep[0])
    period_str = " ".join(no_entities_text.split(" ")[1:]) if no_entities_text else None
    period = DurationParser.parse(period_str) if period_str else None
    expire_date = (datetime.now(timezone.utc) + period) if isinstance(period, timedelta) else None

    reason = "\n".join(text_sep[1:]) if len(text_sep) > 1 else None

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
    
    if target_user.is_bot:
        await msg.reply("❌ Вы не можете выдать варн боту.")
        return

    warn_id = await add_warning(chat_id, int(target_user.id), admin_id, reason, expire_date)
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    formatted_period = f"на {TimedeltaFormatter.format(period, suffix='none')}" if isinstance(period, timedelta) else "навсегда"

    # Определяем статус опасности
    max_warns = await get_max_warns(int(msg.chat.id))
    if warn_id and warn_id >= max_warns:
        status = "🔴 КРИТИЧНЫЙ"
    elif warn_id and warn_id >= (max_warns/2):
        status = "🟠 ПОВЫШЕН"
    else:
        status = "🟡 НОРМА"

    ans = f"✅ Варн выдан {mention}\n\n"
    ans += f"📌 Причина: {reason or 'не указана'}\n"
    ans += f"⏰ Период: {formatted_period}\n"

    if warn_id:
        ans += f"🆔 Номер: #{warn_id}\n"
        ans += f"📛 Уровень нарушений: {status}"
        
        if warn_id >= max_warns:
            ans += f"\n\n🚨 У пользователя {max_warns} и более варнов! Рекомендуется бан."

    await msg.reply(ans, parse_mode="HTML")

@router.message(
    F.text.regexp(r"^-варн(?:\s|$)", flags=re.IGNORECASE)
)
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
    
    if target_user.is_bot:
        await msg.reply("❌ Эта команда не работает с ботами.")
        return

    success = await remove_warning(chat_id, int(target_user.id), warn_index)
    if success:
        warn_info = f" #{warn_index+1}" if warn_index is not None else ""
        await msg.reply(f"✅ Варн{warn_info} снят.", parse_mode="HTML")
    else:
        if warn_index is not None:
            await msg.reply(f"⚠️ Варн #{warn_index+1} не существует.", parse_mode="HTML")
        else:
            await msg.reply(f"ℹ️ Предупреждений не найдено.", parse_mode="HTML")

@router.message(
    F.text.lower().startswith("амнистия")
)
async def do_amnesty(msg: Message):
    """Команда: амнистия"""
    bot = msg.bot
    admin_id = int(msg.from_user.id)
    chat_id = int(msg.chat.id)

    is_admin_user = await is_creator(bot, chat_id, admin_id)
    if not is_admin_user:
        await msg.reply("❌ Только создатель чата может использовать эту команду.")
        return

    await amnesty(chat_id)
    await msg.reply(f"✅ Все варны очищены.", parse_mode="HTML")
