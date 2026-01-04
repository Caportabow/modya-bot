import re
import random
from aiogram import Router, F
from aiogram.types import Message

from db.users import get_random_chat_member
from utils.telegram.users import mention_user

router = Router(name="game_commands")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(
    F.text.regexp(r"^инфа(?:\s|$)", flags=re.IGNORECASE)
)
async def info(msg: Message):
    """Команда: инфа {текст}"""
    emojis = ["🎲", "🔮", "💡", "🎱", "🎰"]
    responses = [
        "Я думаю что вероятность {percentage}%",
        "Шансы на это составляют {percentage}%",
        "По-моему, вероятность около {percentage}%",
        "Вероятность примерно {percentage}%",
        "Я бы сказал {percentage}%",
    ]
    
    percentage = random.randint(0, 100)
    response_template = random.choice(responses).format(percentage=percentage)
    emoji = random.choice(emojis)

    await msg.reply(f"{emoji} • {response_template}", parse_mode="HTML")

@router.message(
    F.text.regexp(r"^кто(?:\s|$)", flags=re.IGNORECASE)
)
async def whois(msg: Message):
    """Команда: кто {текст}"""
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2: return
    
    arg = parts[1].strip()
    if len(arg) > 500:
        await msg.reply("❌ Слишком длинный аргумент (макс 500 символов)")
        return
    
    emojis = ["🎲", "🔮", "💡", "🎱", "🎰"]
    responses = [
        "Я думаю, что",
        "Мне кажется",
        "По-моему",
        "Наверное,",
        "Похоже, что"
    ]

    member = await get_random_chat_member(int(msg.chat.id))
    if not member:
        await msg.reply("❗ В чате недостаточно пользователей для выполнения этой команды.")
        return
    
    response_template = random.choice(responses)
    member_mention = await mention_user(bot=msg.bot, chat_id=int(msg.chat.id), user_id=member)
    emoji = random.choice(emojis)

    await msg.reply(f"{emoji} • {response_template} {member_mention} {arg}", parse_mode="HTML")
