from aiogram import Router, F
from aiogram.types import Message

from datetime import timedelta

from utils.telegram.users import mention_user_with_delay
from utils.time import get_duration, format_timedelta
from db.messages.cleaning import minmsg_users, verify_cleaning_possibility, inactive_users

from config import MAX_MESSAGE_LENGTH

router = Router(name="cleaning")


@router.message((F.text.lower().startswith("норма ")) & (F.chat.type.in_(["group", "supergroup"])))
async def minmsg_handler(msg: Message):
    """Команда: норма {кол-во сообщений}"""
    bot = msg.bot
    parts = msg.text.split()
    chat_id = int(msg.chat.id)
    if len(parts) > 1:
        msg_count = parts[1]
        if not msg_count.isdigit() or int(msg_count) <= 0:
            await msg.reply("❌ Укажите корректное число сообщений.")
            return
    else:
        await msg.reply("❌ Укажите минимальное количество сообщений (норму).")
        return
    
    possibility = await verify_cleaning_possibility(chat_id)
    if not possibility:
        await msg.reply("❌ Бот должен находиться в чате минимум неделю, прежде чем сможет проводить чистку.")
        return

    users = await minmsg_users(chat_id, int(msg_count))

    if not users or len(users) == 0:
        await msg.reply(f"✅ Все участники успешно набрали норму!")
        return

    ans_header = f"❗️Следующие участники не набрали норму в {msg_count} сообщений:\n\n"
    ans = ans_header
    for i, u in enumerate(users):
        mention = await mention_user_with_delay(bot=bot, chat_id=int(msg.chat.id), user_id=int(u["user_id"]))
        line = f"{i+1}. {mention} ({u['count']} соо.)\n"

        # если добавление строки превысит лимит — отправляем текущее сообщение и начинаем новое
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            await msg.reply(ans, parse_mode="HTML")
            ans = ""  # сбрасываем накопленное сообщение

        ans += line

    # отправляем остаток, если есть
    if ans.strip():
        await msg.reply(ans, parse_mode="HTML")

@router.message((F.text.lower().startswith("неактив ")) & (F.chat.type.in_(["group", "supergroup"])))
async def inactive_handler(msg: Message):
    """Команда: неактив {период}"""
    bot = msg.bot
    parts = msg.text.split()
    chat_id = int(msg.chat.id)
    if len(parts) > 1:
        duration = get_duration(" ".join(parts[1:]))
        if not duration or not isinstance(duration, timedelta):
            await msg.reply("❌ Укажите период корректно.")
            return
    else:
        duration = timedelta(days=4)
    
    possibility = await verify_cleaning_possibility(chat_id)
    if not possibility:
        await msg.reply("❌ Бот должен находиться в чате минимум неделю, прежде чем сможет проводить чистку.")
        return

    users = await inactive_users(chat_id, duration)

    if not users or len(users) == 0:
        await msg.reply(f"✅ Все участники акивны!")
        return

    ans_header = f"❗️Следующие участники не активили последние {format_timedelta(duration, adder=False)}:\n\n"
    ans = ans_header
    for i, u in enumerate(users):
        mention = await mention_user_with_delay(bot=bot, chat_id=int(msg.chat.id), user_id=int(u["user_id"]))
        line = f"{i+1}. {mention} ({u['last_message_date']})\n"

        # если добавление строки превысит лимит — отправляем текущее сообщение и начинаем новое
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            await msg.reply(ans, parse_mode="HTML")
            ans = ""  # сбрасываем накопленное сообщение

        ans += line

    # отправляем остаток, если есть
    if ans.strip():
        await msg.reply(ans, parse_mode="HTML")