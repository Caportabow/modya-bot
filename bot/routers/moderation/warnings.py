import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from datetime import datetime, timezone

from services.telegram.user_permissions import is_admin, is_creator
from services.messaging.warnings import generate_all_warnings_msg, generate_user_warnings_msg
from services.telegram.chat_member import get_chat_member
from services.telegram.user_mention import mention_user
from services.telegram.user_parser import parse_user_mention
from services.telegram.keyboards.pagination import Pagination

from config import WARNINGS_PICTURE_ID
from services.time_utils import DurationParser, TimedeltaFormatter

from db.chats.settings import get_max_warns
from db.warnings import add_warning, remove_warning, amnesty

router = Router(name="warnings")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(
    F.text.lower() == "все варны"
)
async def stats_handler(msg: Message):
    """Команда: все варны"""
    bot = msg.bot

    text, keyboard = await generate_all_warnings_msg(bot, int(msg.chat.id), 1)
    if not text:
        await msg.reply("❌ У пользователей этого чата нет варнов.")
        return
    
    await msg.reply_photo(photo=WARNINGS_PICTURE_ID, parse_mode="HTML", caption=text, reply_markup=keyboard)

@router.message(
    F.text.lower().startswith("варны")
)
async def get_user_warnings_handler(msg: Message):
    """Команда: варны @user"""
    bot = msg.bot
    target_user = None
    chat_id = int(msg.chat.id)

    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user: target_user = msg.from_user

    if target_user.is_bot:
        await msg.reply("❌ Вы не можете просмотреть варны бота.")
        return
    
    text, keyboard = await generate_user_warnings_msg(bot, chat_id, target_user, 1)
    if not text:
        mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
        await msg.reply(f"❕У пользователя {mention} нет варнов.", parse_mode="HTML")
        return

    await msg.reply_photo(photo=WARNINGS_PICTURE_ID, caption=text, parse_mode="HTML", reply_markup=keyboard)

@router.message(
    F.text.regexp(r"^\+варн(?:\s|$)", flags=re.IGNORECASE)
)
async def add_warning_handler(msg: Message):
    """Команда: +варн {период} @user {отступ} {причина}"""
    bot = msg.bot
    admin_id = int(msg.from_user.id)
    chat_id = int(msg.chat.id)
    target_user = None

    # Отделяем тело команды
    m = re.match(r"^\+варн\b(.*)", msg.text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return

    body = m.group(1)

    # Делим аргументы и причину
    parts = body.lstrip("\n").split("\n", 1)
    args = parts[0].strip()
    reason = parts[1].strip() if len(parts) == 2 else None

    # Извлекаем период
    period_str = None
    for token in args.split():
        if not token.startswith("@"):
            period_str = token
            break

    period = DurationParser.parse(period_str) if period_str else None
    expire_date = (datetime.now(timezone.utc) + period) if period else None

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
    formatted_period = f"на {TimedeltaFormatter.format(period, suffix='none')}" if period else "навсегда"

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
    F.text.lower() == "амнистия"
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

@router.callback_query(Pagination.filter(F.subject == "all_warnings"))
async def all_warnings_pagination_handler(callback: CallbackQuery, callback_data: Pagination):
    text, keyboard = await generate_all_warnings_msg(callback.bot, int(callback.message.chat.id), callback_data.page)

    if text:
        await callback.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer("") # пустой ответ, чтобы убрать "часики"
    
    else:
        await callback.answer(text="❌ Неизвестная ошибка.", show_alert=True)

@router.callback_query(Pagination.filter((F.subject == "user_warnings") & (F.is_back_button == False)))
async def user_warnings_pagination_handler(callback: CallbackQuery, callback_data: Pagination):
    bot = callback.bot
    chat_id = int(callback.message.chat.id)
    member = await get_chat_member(bot = bot, chat_id = chat_id, user_id = callback_data.query)
    if not member: return

    text, keyboard = await generate_user_warnings_msg(callback.bot, callback.message.chat.id, member.user, callback_data.page, callback_data.with_back_button)
    if text:
        await callback.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer("") # пустой ответ, чтобы убрать "часики"
    
    else:
        await callback.answer(text="❌ Неизвестная ошибка.", show_alert=True)
