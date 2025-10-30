from aiogram import Router, F
from aiogram.types import Message

from utils.telegram.users import mention_user
from db import minmsg_users

router = Router(name="cleaning")


@router.message((F.text.lower().startswith("норма")) & (F.chat.type.in_(["group", "supergroup"])))
async def minmsg_handler(msg: Message):
    """Команда: норма {кол-во сообщений}"""
    bot = msg.bot
    parts = msg.text.split()
    if len(parts) > 1:
        msg_count = parts[1]
        if not msg_count.isdigit() or int(msg_count) <= 0:
            await msg.reply("❌ Укажите корректное число сообщений.")
            return
    else:
        await msg.reply("❌ Укажите минимальное количество сообщений (норму).")
        return
    
    users = await minmsg_users(int(msg.chat.id), int(msg_count))
    if not users or len(users) == 0:
        await msg.reply(f"✅ Все участники успешно набрали норму!")
        return
    ans = f"❗️Следующие участники не набрали норму в {msg_count} сообщений:\n\n"
    for i, u in enumerate(users):
        mention = await mention_user(bot=bot, chat_id=int(msg.chat.id), user_id=int(u["user_id"]))
        ans += f"{i+1}. {mention} - {u["count"]} сообщений\n"

    await msg.reply(ans, parse_mode="HTML")
