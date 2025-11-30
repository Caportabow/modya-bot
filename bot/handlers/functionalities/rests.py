from aiogram import Router, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, InlineKeyboardButton

from datetime import timedelta, datetime, timezone

from utils.telegram.users import mention_user, parse_user_mention, is_admin, is_creator, mention_user_with_delay
from utils.time import get_duration, format_timedelta
from db.messages.statistics import user_stats
from db.users.rests import set_rest, get_all_rests
from config import MAX_MESSAGE_LENGTH

router = Router(name="rests")


@router.message((F.text.lower().startswith("ресты")) & (F.chat.type.in_(["group", "supergroup"])))
async def stats_handler(msg: Message):
    """Команда: ресты"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    rests = await get_all_rests(chat_id)

    if not rests or len(rests) == 0:
        await msg.reply(f"✅ В этом чате нету участников с активным рестом.")
        return

    ans_header = f"❗️Следующие участники находяться в ресте:\n\n"
    ans = ans_header
    for i, r in enumerate(rests):
        mention = await mention_user_with_delay(bot=bot, chat_id=chat_id, user_id=int(r["user_id"]))
        line = f"{i+1}. {mention} - {r['rest']}\n"

        # если добавление строки превысит лимит — отправляем текущее сообщение и начинаем новое
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            await msg.reply(ans, parse_mode="HTML")
            ans = ""  # сбрасываем накопленное сообщение

        ans += line

    # отправляем остаток, если есть
    if ans.strip():
        await msg.reply(ans, parse_mode="HTML")

@router.message((F.text.lower().startswith("взять рест")) & (F.chat.type.in_(["group", "supergroup"])))
async def ask_for_rest(msg: Message):
    """Команда: взять рест {период}"""
    bot = msg.bot
    parts = msg.text.split()
    duration = None

    target_user = msg.from_user

    # Проверяем, указан ли период пользователем
    if len(parts) > 2:
        rest_info = " ".join(parts[2:])
        duration = get_duration(rest_info)
    else:
        await msg.reply("❌ Укажите длительность реста (взять рест {период}).")
        return

    if duration is None:
        await msg.reply("❌ Не удалось распознать период.")
        return
    
    if isinstance(duration, str):
        await msg.reply("❌ Вы не можете взять рест навсегда.")
        return
    
    if duration < timedelta(days=1):
        await msg.reply("❌ Вы не можете взять рест на период меньше одной добы.")
        return
    
    if duration > timedelta(days=365):
        await msg.reply("❌ Вы не можете взять рест на период больше года.")
        return

    # Определяем временной диапазон
    beauty_until = format_timedelta(duration, adder=False)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"rest,{rest_info}"),
        InlineKeyboardButton(text="❌ Отказать", callback_data=f"rest,decline")
    )
    builder.row(
        InlineKeyboardButton(text="🏃 Отозвать просьбу", callback_data=f"rest,retire")
    )

    stats = await user_stats(int(msg.chat.id), int(target_user.id))
    mention = await mention_user(bot=bot, user_entity=target_user)

    ans = f"👤 Пользователь {mention}\n"
    ans += f"С активом (24ч|7дн|30дн|∞): {stats["activity"]}\n\n"
    ans += f"Запросил рест на {beauty_until}"
    
    await msg.reply(text=ans, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.message((F.text.lower().startswith("+рест")) & (F.chat.type.in_(["group", "supergroup"])))
async def give_rest(msg: Message):
    """Команда: +рест @user {период}"""
    bot = msg.bot
    parts = msg.text.split()
    chat_id = int(msg.chat.id)
    trigger_user_id = int(msg.from_user.id)
    duration = None
    
    duration = get_duration(" ".join(parts[1:]))

    if duration is None:
        await msg.reply("❌ Не удалось распознать период.")
        return
    
    if isinstance(duration, str):
        await msg.reply("❌ Вы не можете выдать рест навсегда.")
        return
    
    if duration < timedelta(days=1):
        await msg.reply("❌ Вы не можете выдать рест на период меньше одной добы.")
        return
    
    target_user = await parse_user_mention(bot, msg)

    if msg.reply_to_message and not target_user:
        target_user = msg.reply_to_message.from_user

    if not target_user:
        await msg.reply("❌ Укажите пользователя, которому хотите выдать рест.")
        return
    
    if target_user.is_bot:
        await msg.reply("❌ Вы не можете выдать рест боту.")
        return
    
    target_user_id = int(target_user.id)

    if target_user_id == trigger_user_id:
        creator = await is_creator(bot, chat_id, trigger_user_id)
        if not creator:
            await msg.reply("❌ Вы не можете выдать рест самому себе.")
            return

    admin = await is_admin(bot, chat_id, trigger_user_id)
    if not admin:
        await msg.reply("❌ Вы должны быть админом, чтобы выдать рест.")
        return
    
    # Определяем временной диапазон
    until = datetime.now(timezone.utc) + duration
    beauty_until = format_timedelta(duration, adder=False)

    await set_rest(chat_id, target_user_id, date = until)
    mention = await mention_user(bot=bot, user_entity=target_user)

    ans = f"⏰ Пользователю {mention} успешно выдан рест на {beauty_until}"
    await msg.reply(ans, parse_mode="HTML")

@router.message((F.text.lower().startswith("-рест")) & (F.chat.type.in_(["group", "supergroup"])))
async def remove_rest(msg: Message):
    """Команда: -рест @user"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    trigger_user_id = int(msg.from_user.id)

    target_user = await parse_user_mention(bot, msg)

    if msg.reply_to_message and not target_user:
        target_user = msg.reply_to_message.from_user

    if not target_user:
        target_user = msg.from_user
    
    if target_user.is_bot:
        await msg.reply("❌ Эта команда не работает с ботами.")
        return
    
    target_user_id = int(target_user.id)

    if target_user_id != trigger_user_id:
        admin = await is_admin(bot, chat_id, trigger_user_id)
        if not admin:
            await msg.reply("❌ Вы должны быть админом, чтобы выдать рест.")
            return
        
        mention = await mention_user(bot=bot, user_entity=target_user)
        ans = f"⏰ {mention}, ваш рест был снят. Добро пожаловать обратно!"
    else:
        ans = f"✅ Рест снят успешно."

    await set_rest(chat_id, target_user_id, date = None)
    await msg.reply(ans, parse_mode="HTML")
