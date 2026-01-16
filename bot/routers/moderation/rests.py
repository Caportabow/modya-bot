import re
from aiogram import Router, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton

from datetime import timedelta, datetime, timezone

from utils.telegram.users import mention_user, parse_user_mention, is_admin, is_creator, mention_user_with_delay
from utils.telegram.message_templates import describe_rest, generate_rest_msg
from utils.time import DurationParser, TimedeltaFormatter
from db.messages.statistics import user_stats
from db.users.rests import add_rest, remove_rest, get_all_rests, get_user_rest
from config import MAX_MESSAGE_LENGTH

router = Router(name="rests")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(
        F.text.lower() == "ресты"
)
async def rests_handler(msg: Message):
    """Команда: ресты"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    rests = await get_all_rests(chat_id)

    if not rests or len(rests) == 0:
        await msg.reply(f"❗️ В этом чате нету активных рестов.")
        return

    now = datetime.now(timezone.utc)
    ans_header = f"💤 Пользователи в ресте:\n\n"
    ans = ans_header
    ans += "<blockquote expandable>"


    for i, r in enumerate(rests):
        mention = await mention_user_with_delay(bot=bot, chat_id=chat_id, user_id=int(r["user_id"]))
        rest_info = f"до {r['valid_until']:%d.%m.%Y} (еще {TimedeltaFormatter.format(r['valid_until'] - now, suffix="none")})"
        line = f"▫️ {mention} - {rest_info}\n"

        # если добавление строки превысит лимит — отправляем текущее сообщение и начинаем новое
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            ans += "</blockquote>"
            await msg.reply(ans, parse_mode="HTML")
            ans = ans_header  # сбрасываем накопленное сообщение
            ans += "<blockquote expandable>"

        ans += line

    # отправляем остаток, если есть
    if ans.strip():
        ans += "</blockquote>"
        await msg.reply(ans, parse_mode="HTML")

@router.message(
    F.text.regexp(r"^взять рест(?:\s|$)", flags=re.IGNORECASE)
)
async def ask_for_rest(msg: Message):
    """Команда: взять рест {период}"""
    bot = msg.bot
    parts = msg.text.split()
    duration = None

    target_user = msg.from_user

    # Проверяем, указан ли период пользователем
    if len(parts) <= 2:
        await msg.reply("❌ Укажите длительность реста (взять рест {период}).")
        return
    
    rest_info = " ".join(parts[2:])
    duration = DurationParser.parse(rest_info)

    if duration is None:
        # команда вероятно сработала случайно, останавливаем обработку
        return
    
    if duration < timedelta(days=1):
        await msg.reply("❌ Вы не можете взять рест на период меньше одной добы.")
        return
    
    if duration > timedelta(days=365):
        await msg.reply("❌ Вы не можете взять рест на период больше года.")
        return

    stats = await user_stats(int(msg.chat.id), int(target_user.id))
    if not stats:
        await msg.reply(text="❌ Неизвестная ошибка. Попробуйте снова.", parse_mode="HTML")
        return

    # Определяем временной диапазон
    beauty_until = TimedeltaFormatter.format(duration, suffix="none")

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"rest,{rest_info}"),
        InlineKeyboardButton(text="❌ Отказать", callback_data=f"rest,decline")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Отозвать", callback_data=f"rest,retire")
    )
    mention = await mention_user(bot=bot, chat_id=int(msg.chat.id), user_entity=target_user)

    ans = f"👤 Пользователь {mention}\n"
    ans += f"📈 С активом (24ч|7дн|30дн|∞): {stats["activity"]["day_count"]} | {stats["activity"]["week_count"]} | {stats["activity"]["month_count"]} | {stats["activity"]["total"]}\n\n"
    ans += f"⏰ Запрашивает рест на {beauty_until}"
    
    await msg.reply(text=ans, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.message(
    F.text.regexp(r"^\+рест(?:\s|$)", flags=re.IGNORECASE)
)
async def give_rest(msg: Message):
    """Команда: +рест @user {период}"""
    bot = msg.bot
    parts = msg.text.split()
    chat_id = int(msg.chat.id)
    trigger_user_id = int(msg.from_user.id)
    duration = None
    
    duration = DurationParser.parse(" ".join(parts[1:]))

    if duration is None:
        await msg.reply("❌ Не удалось распознать период.")
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
    beauty_until = TimedeltaFormatter.format(duration, suffix="none")

    await add_rest(chat_id, target_user_id, administrator_user_id=trigger_user_id, valid_until=until)
    user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    administrator_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=msg.from_user)

    ans = f"⏰ Пользователю {user_mention} успешно выдан рест.\n"
    ans += f"📅 До: {until:%d.%m.%Y} (еще {beauty_until})\n"
    ans += f"👮 Администратор: {administrator_mention}."
    await msg.reply(ans, parse_mode="HTML")

@router.message(
    F.text.regexp(r"^-рест(?:\s|$)", flags=re.IGNORECASE)
)
async def remove_rest_handler(msg: Message):
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
            await msg.reply("❌ Вы должны быть админом, чтобы снять чужой рест.")
            return

        user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
        administrator_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=msg.from_user)

        ans = f"⏰ Рест {user_mention} снят.\n"
        ans += f"👮 Администратор: {administrator_mention}\n"
    else:
        ans = f"🔓 Рест снят успешно."

    await remove_rest(chat_id, target_user_id)
    await msg.reply(ans, parse_mode="HTML")

@router.message(
    F.text.lower().startswith("мой рест")
)
async def my_rest_handler(msg: Message):
    """Команда: мой рест"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    rest = await get_user_rest(chat_id, msg.from_user.id)

    if not rest:
        await msg.reply(f"❗️ У вас нет активного реста.")
        return

    ans = await describe_rest(bot=bot, chat_id=chat_id, target_user_entity=msg.from_user, rest=rest)
    
    await msg.reply(ans, parse_mode="HTML")

@router.message(
    F.text.regexp(r"^рест(?:\s|$)")
)
async def user_rest_handler(msg: Message):
    """Команда: рест {упоминание}"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    target_user = await parse_user_mention(bot, msg)

    if msg.reply_to_message and not target_user:
        target_user = msg.reply_to_message.from_user
    
    if not target_user:
        await msg.reply("❌ Укажите пользователя, рест которого хотите просмотреть.")
        return

    if target_user.is_bot:
        await msg.reply("❌ Вы не можете просмотреть рест бота.")
        return
    rest = await get_user_rest(chat_id, target_user.id)

    if not rest:
        await msg.reply(f"❗️ У этого пользователя нету активного реста.")
        return

    ans = await describe_rest(bot=bot, chat_id=chat_id, target_user_entity=target_user, rest=rest)
    
    await msg.reply(ans, parse_mode="HTML")


@router.callback_query(F.data.startswith("rest"))
async def rest_callback_handler(callback: CallbackQuery):
    """Обрабатывает выдачу реста."""
    bot = callback.bot
    msg = callback.message
    parts = callback.data.split(",")

    # Unknown error
    if not msg or not msg.chat or len(parts) < 4: return

    chat_id = int(msg.chat.id)
    data = parts[1]
    trigger_user = callback.from_user
    target_user = msg.reply_to_message.from_user
    trigger_user_id = int(trigger_user.id)

    if data == "retire":
        if trigger_user_id != int(target_user.id):
            await callback.answer(text="❌ Вы не можете нажать на эту кнопку.", show_alert=True)
            return
        
        await msg.delete()
        return

    # Проверка на самого себя
    if trigger_user_id == int(target_user.id):
        creator = await is_creator(bot, chat_id, trigger_user_id)
        if not creator:
            await msg.reply("❌ Вы не можете выдать рест самому себе.", parse_mode="HTML")
            return

    # Проверка прав администратора
    admin = await is_admin(bot, chat_id, trigger_user_id)
    if not admin:
        await msg.reply(text="❌ Вы должны быть админом, чтобы выдать рест.", parse_mode="HTML")
        return

    ans = await generate_rest_msg(bot, chat_id, data, trigger_user, target_user)
    
    await msg.edit_reply_markup()
    await msg.edit_text(text=ans, parse_mode="HTML")
