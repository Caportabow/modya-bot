import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from datetime import datetime, timezone

from config import AWARDS_PICTURE_ID, WARNINGS_PICTURE_ID
from db.messages import plot_user_activity

from services.messages.warnings import generate_user_warnings_msg

from utils.time import TimedeltaFormatter
from utils.telegram.message_templates import generate_awards_msg, family_tree
from utils.telegram.users import parse_user_mention, mention_user, get_chat_member_or_fall
from utils.web.activity_chart import make_activity_chart

from utils.telegram.keyboards import get_user_info_keyboard, UserInfo, Pagination
from db.messages.statistics import user_stats, get_favorite_word
from db.users import get_uid

router = Router(name="user_info")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(
    F.text.regexp(r"^(кто я|кто ты)(\s+@?\S+)?$", flags=re.IGNORECASE)
)
async def user_info_handler(msg: Message):
    """Команда: кто [я|ты]"""
    bot = msg.bot
    m = re.match(r"^(кто)\s+(я|ты)(?:\s+(.*))?$", msg.text.lower())
    if not m: return

    target = m.group(2)
    
    if target == "я":
        user = msg.from_user

    elif target == "ты":
        if msg.reply_to_message:
            user = msg.reply_to_message.from_user
        else:
            user = await parse_user_mention(bot, msg)
            if not user:
                await msg.reply("❌ Укажи пользователя реплаем или упоминанием.")
                return

    if user.is_bot:
        await msg.reply("❌ Эта команда не поддерживает ботов.")
        return
    
    chat_id = int(msg.chat.id)
    user_id = int(user.id)
    
    stats = await user_stats(chat_id, user_id)

    user_activity = await plot_user_activity(chat_id=chat_id, user_id=user_id)
    img = await make_activity_chart(user_activity)

    fav_word = await get_favorite_word(chat_id, user_id)
    if not stats or not img:
        await msg.reply("❌ Нет данных по этому пользователю.")
        return
    
    now = datetime.now(timezone.utc)
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=user)

    ans = f"👤 Это пользователь {mention}\n\n"
    if fav_word:
        fav_word_count = fav_word["count"]
        fav_word = fav_word["word"]

        fav_user_id = await get_uid(chat_id, fav_word)

        if not fav_user_id:
            ans += f"Любимое слово: {fav_word} ({fav_word_count} р.)\n"
        else:
            fav_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=int(fav_user_id))
            ans += f"Любимый юзер: {fav_user_mention} ({fav_word_count} р.)\n"
    else: ans += f"Любимое слово: (данных недостаточно)\n"
    ans += f"Дебют: {stats["first_seen"]:%d.%m.%Y} ({TimedeltaFormatter.format(now - stats["first_seen"])})\n"
    ans += f"Последний актив: { TimedeltaFormatter.format(now - stats["last_active"])}\n"

    if stats["rest"]:
        ans += f"Рест: до {stats["rest"]:%d.%m.%Y} (еще {TimedeltaFormatter.format(stats["rest"] - now, suffix="none")})\n"
    else:
        ans += f"Рест: (не активен)\n"

    ans += f"Актив (24ч|7дн|30дн|∞): {stats["activity"]["day_count"]} | {stats["activity"]["week_count"]} | {stats["activity"]["month_count"]} | {stats["activity"]["total"]}\n"

    uploaded_img = BufferedInputFile(img, filename="stats.png")

    keyboard = await get_user_info_keyboard(user_id)

    await bot.send_photo(chat_id=msg.chat.id,
                photo=uploaded_img,
                caption=ans, reply_to_message_id=msg.message_id,
                reply_markup=keyboard,
                parse_mode="HTML"
    )

@router.callback_query(
    UserInfo.filter(F.secondary_action == "family")
)
async def user_family_info_callback_handler(callback: CallbackQuery, callback_data: UserInfo):
    """Обрабатывает запрос об семье пользователя."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return
    user_info = callback_data
    chat_id = int(msg.chat.id)
    user_id = user_info.user_id

    member = await get_chat_member_or_fall(bot = bot, chat_id = chat_id, user_id = user_id)
    if not member:
        return

    user = member.user
    
    await family_tree(bot, chat_id, user_id, user)

@router.callback_query(
    UserInfo.filter(F.secondary_action == "awards")
)
async def user_awards_info_callback_handler(callback: CallbackQuery, callback_data: UserInfo):
    """Обрабатывает запросы об наградах пользователя."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return
    user_info = callback_data
    chat_id = int(msg.chat.id)
    user_id = user_info.user_id

    member = await get_chat_member_or_fall(bot = bot, chat_id = chat_id, user_id = user_id)
    if not member:
        return

    user = member.user
    
    answers = await generate_awards_msg(bot, chat_id, user)
    photo = AWARDS_PICTURE_ID

    for ans in answers:
        await msg.reply_photo(
            photo=photo, 
            caption=ans, 
            reply_to_message_id=msg.message_id, 
            parse_mode="HTML"
        )

@router.callback_query(
    UserInfo.filter(F.secondary_action == "warnings")
)
async def user_warnings_info_callback_handler(callback: CallbackQuery, callback_data: UserInfo):
    """Обрабатывает запросы об предупрежденях пользователя."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return
    user_info = callback_data
    chat_id = int(msg.chat.id)
    user_id = user_info.user_id

    member = await get_chat_member_or_fall(bot = bot, chat_id = chat_id, user_id = user_id)
    if not member:
        return

    text, keyboard = await generate_user_warnings_msg(bot, chat_id, member.user, 1, True)
    if not text:
        await callback.answer(text="❌ Неизвестная ошибка.", show_alert=True)

    await msg.edit_caption(
        photo=WARNINGS_PICTURE_ID, 
        caption=text, 
        reply_to_message_id=msg.message_id, 
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(Pagination.filter(F.subject == "user_rests" & F.back_button == True))
async def user_info_back_pagination_handler(callback: CallbackQuery, callback_data: Pagination):
    # TODO
    pass
