import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from datetime import timedelta, datetime, timezone

from services.messages.rests import generate_all_rests_msg, generate_rest_description_msg

from utils.telegram.keyboards import get_rest_request_keyboard, RestRequest, deserialize_timedelta, Pagination
from utils.telegram.users import mention_user, parse_user_mention, is_admin, is_creator
from utils.time import DurationParser, TimedeltaFormatter
from db.messages.statistics import user_stats
from db.users.rests import add_rest, remove_rest

router = Router(name="rests")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(
        F.text.lower() == "ресты"
)
async def rests_handler(msg: Message):
    """Команда: ресты"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    
    text, keyboard = await generate_all_rests_msg(bot, chat_id, 1)

    if not text:
        await msg.reply(f"❗️ В этом чате нету активных рестов.")
        return

    await msg.reply(text, parse_mode="HTML", reply_markup=keyboard)

@router.message(
    F.text.regexp(r"^взять рест(?:\s|$)", flags=re.IGNORECASE)
)
async def ask_for_rest(msg: Message):
    """Команда: взять рест {период}"""
    bot = msg.bot
    duration_text = re.sub(
        r"^взять рест\s*", "", msg.text, flags=re.IGNORECASE
    ).strip()
    duration = None

    target_user = msg.from_user

    # Проверяем, указан ли период пользователем
    if not duration_text:
        await msg.reply("❌ Укажите длительность реста (взять рест {период}).")
        return
    
    duration = DurationParser.parse(duration_text)

    if duration is None:
        if DurationParser.parse_forever(duration_text):
            await msg.reply("❌ Вы не можете взять рест без срока окончания.")
            return
        
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
    keyboard = await get_rest_request_keyboard(duration)
    mention = await mention_user(bot=bot, chat_id=int(msg.chat.id), user_entity=target_user)

    ans = f"👤 Пользователь {mention}\n"
    ans += f"📈 С активом (24ч|7дн|30дн|∞): {stats["activity"]["day_count"]} | {stats["activity"]["week_count"]} | {stats["activity"]["month_count"]} | {stats["activity"]["total"]}\n\n"
    ans += f"⏰ Запрашивает рест на {beauty_until}"
    
    await msg.reply(text=ans, reply_markup=keyboard, parse_mode="HTML")

@router.message(
    F.text.regexp(r"^\+рест(?:\s|$)", flags=re.IGNORECASE)
)
async def give_rest(msg: Message):
    """Команда: +рест @user {период}"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    trigger_user_id = int(msg.from_user.id)
    duration = None

    parts = msg.text.split(maxsplit=2)
    # parts:
    # ["+рест", "два", "дня"] → если без @user
    # ["+рест", "@user", "два дня"] → если с @user
    if len(parts) < 2:
        await msg.reply("❌ Укажите период реста.")
        return

    if parts[1].startswith("@"):
        if len(parts) < 3:
            await msg.reply("❌ Укажите период реста.")
            return
        period = " ".join(parts[2:]).strip()
    else:
        period = " ".join(parts[1:]).strip()
    
    duration = DurationParser.parse(period)
    if duration is None:
        if DurationParser.parse_forever(period):
            await msg.reply("❌ Вы не можете выдать рест навсегда.")
        else:
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
        ans = f"⏰ Рест снят успешно."

    await remove_rest(chat_id, target_user_id)
    await msg.reply(ans, parse_mode="HTML")

@router.message(
    F.text.lower().startswith("мой рест")
)
async def my_rest_handler(msg: Message):
    """Команда: мой рест"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    text = await generate_rest_description_msg(bot=bot, chat_id=chat_id, target_user_entity=msg.from_user)

    if not text:
        await msg.reply(f"❗️ У вас нет активного реста.")
        return

    await msg.reply(text, parse_mode="HTML")

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
    
    text = await generate_rest_description_msg(bot=bot, chat_id=chat_id, target_user_entity=target_user)
    if not text:
        await msg.reply(f"❗️ У этого пользователя нету активного реста.")
        return

    await msg.reply(text, parse_mode="HTML")


@router.callback_query(RestRequest.filter(F.response == "accept"))
async def rest_request_accept_callback_handler(callback: CallbackQuery, callback_data: RestRequest):
    """Обрабатывает согласие на выдачу реста."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return

    chat_id = int(msg.chat.id)
    trigger_user = callback.from_user
    target_user = msg.reply_to_message.from_user
    trigger_user_id = int(callback.from_user.id)

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

    trigger_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=trigger_user)
    target_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    
    delta = deserialize_timedelta(callback_data.delta)
    if delta < timedelta(days=1):
        ans = "❌ Вы не можете выдать рест на период меньше одной добы."
    
    else:
        until = datetime.now(timezone.utc) + delta
        beauty_until = TimedeltaFormatter.format(delta, suffix="none")

        await add_rest(chat_id, int(target_user.id), administrator_user_id=int(trigger_user.id), valid_until=until)

        ans = (
            f"⏰ Пользователю {target_user_mention} успешно выдан рест.\n"
            f"📅 До: {until:%d.%m.%Y} (еще {beauty_until})\n"
            f"👮 Администратор: {trigger_user_mention}."
        )
        
    await msg.edit_reply_markup()
    await msg.edit_text(text=ans, parse_mode="HTML")

@router.callback_query(RestRequest.filter(F.response == "decline"))
async def rest_request_decline_callback_handler(callback: CallbackQuery, callback_data: RestRequest):
    """Обрабатывает отказ в выдаче реста."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return

    chat_id = int(msg.chat.id)
    trigger_user = callback.from_user
    target_user = msg.reply_to_message.from_user
    trigger_user_id = int(callback.from_user.id)

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

    trigger_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=trigger_user)
    target_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)

    ans = (
        f"❗️ {target_user_mention}, вам отказано в ресте.\n"
        f"👮 Администратор: {trigger_user_mention}."
    )
        
    await msg.edit_reply_markup()
    await msg.edit_text(text=ans, parse_mode="HTML")

@router.callback_query(RestRequest.filter(F.response == "retire"))
async def rest_request_retire_callback_handler(callback: CallbackQuery, callback_data: RestRequest):
    """Обрабатывает отмену запроса на выдачу реста."""
    msg = callback.message
    if not msg or not msg.chat: return

    target_user = msg.reply_to_message.from_user
    trigger_user_id = int(callback.from_user.id)

    if trigger_user_id != int(target_user.id):
        await callback.answer(text="❌ Вы не можете нажать на эту кнопку.", show_alert=True)
        return
    
    await msg.delete()


@router.callback_query(Pagination.filter(F.subject == "all_rests"))
async def all_rests_pagination_handler(callback: CallbackQuery, callback_data: Pagination):
    text, keyboard = await generate_all_rests_msg(callback.bot, int(callback.message.chat.id), callback_data.page)

    if text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    
    else:
        await callback.answer(text="❌ Неизвестная ошибка.", show_alert=True)
