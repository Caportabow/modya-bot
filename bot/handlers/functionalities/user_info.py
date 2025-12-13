import re
from aiogram import Router, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, InlineKeyboardButton, BufferedInputFile
from datetime import datetime, timezone

from utils.time import TimedeltaFormatter
from utils.telegram.users import parse_user_mention, mention_user
from utils.activity_chart import make_activity_chart

from db.messages.statistics import user_stats, get_favorite_word
from db.users import get_uid

router = Router(name="user_info")


@router.message(
    (F.text.regexp(r"^кто(?:\s|$)", flags=re.IGNORECASE)) & 
    (F.chat.type.in_(["group", "supergroup"]))
)
async def user_info_handler(msg: Message):
    """Команда: кто [я|ты]"""
    bot = msg.bot
    parts = msg.text.split()
    if len(parts) <= 1: return
    target = parts[1].lower()
    
    if target == "я": user = msg.from_user

    elif target == "ты" and msg.reply_to_message: user = msg.reply_to_message.from_user

    elif target == "ты" and not msg.reply_to_message and msg.entities:
        user = await parse_user_mention(bot, msg)
        if not user:
            await msg.reply("❌ Не удалось найти пользователя.")
            return
    
    else: return

    if user.is_bot:
        await msg.reply("❌ Эта команда не поддерживает ботов.")
        return
    
    chat_id = int(msg.chat.id)
    user_id = int(user.id)
    
    stats = await user_stats(chat_id, user_id)
    img = await make_activity_chart(chat_id, user_id)
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
    else: ans += f"(данных недостаточно)\n"
    ans += f"Дебют: {stats["first_seen"]:%d.%m.%Y} ({TimedeltaFormatter.format(now - stats["first_seen"])})\n"
    ans += f"Последний актив: { TimedeltaFormatter.format(now - stats["last_active"])}\n"

    if stats["rest"]:
        ans += f"Рест: до {stats["rest"]:%d.%m.%Y} (еще {TimedeltaFormatter.format(stats["rest"] - now, suffix="none")})\n"
    else:
        ans += f"Рест: (не активен)\n"

    ans += f"Актив (24ч|7дн|30дн|∞): {stats["activity"]["day_count"]} | {stats["activity"]["week_count"]} | {stats["activity"]["month_count"]} | {stats["activity"]["total"]}\n"

    uploaded_img = BufferedInputFile(img, filename="stats.png")

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👩‍👩‍👦 Семья", callback_data=f"family,{int(user.id)}"),
    )
    builder.row(
        InlineKeyboardButton(text="🏆 Награды", callback_data=f"awards,{int(user.id)}"),
        InlineKeyboardButton(text="⚠️ Варны", callback_data=f"warnings,{int(user.id)}")
    )

    await bot.send_photo(chat_id=msg.chat.id,
                photo=uploaded_img,
                caption=ans, reply_to_message_id=msg.message_id,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
    )
