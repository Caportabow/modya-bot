from aiogram import Router, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, InlineKeyboardButton, BufferedInputFile

from utils.telegram.users import parse_user_mention, mention_user
from db import user_stats, plot_user_activity, get_uid

router = Router(name="call")


@router.message((F.text.lower().startswith("кто")) & (F.chat.type.in_(["group", "supergroup"])))
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

    stats = await user_stats(int(msg.chat.id), int(user.id))
    img = await plot_user_activity(int(msg.chat.id), int(user.id))
    if not stats or not img:
        if user.is_bot:
            await msg.reply("❌ Эта команда не поддерживает ботов.")
            return
        await msg.reply("❌ Нет данных по этому пользователю.")
        return
    
    mention = await mention_user(bot=bot, chat_id=int(msg.chat.id), user_entity=user)

    ans = f"👤 Это пользователь {mention}\n\n"
    if stats["favorite_word"]:
        fav_word = stats["favorite_word"]["word"]
        fav_word_count = stats["favorite_word"]["count"]

        fav_user_id = await get_uid(int(msg.chat.id), fav_word)

        if not fav_user_id:
            ans += f"Любимое слово: {fav_word} ({fav_word_count} р.)\n"
        else:
            fav_user_mention = await mention_user(bot=bot, chat_id=int(msg.chat.id), user_id=int(fav_user_id))
            ans += f'Любимый участник: {fav_user_mention} ({fav_word_count} р.)\n'
    ans += f"Первое появление: {stats["first_seen"]}\n"
    ans += f"Последний актив: {stats["last_active"]}\n"
    ans += f"Актив за последние (24ч|7дн|30дн|∞): {stats["activity"]}\n"

    uploaded_img = BufferedInputFile(img, filename="stats.png")

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏆 Награды", callback_data=f"awards,{int(user.id)}"),
        InlineKeyboardButton(text="⚠ Варны", callback_data=f"warnings,{int(user.id)}")
    )

    await bot.send_photo(chat_id=msg.chat.id,
                photo=uploaded_img,
                caption=ans, reply_to_message_id=msg.message_id,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
    )
