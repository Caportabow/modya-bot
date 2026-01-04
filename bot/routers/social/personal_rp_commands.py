import re
import emoji
from aiogram import Router, F
from aiogram.types import Message

from config import MAX_RP_COMMANDS_IN_CHAT_PER_USER
from db.users.rp_commands import count_user_commands, upsert_command, delete_rp_command

router = Router(name="personal_rp_commands")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(
    (F.text.regexp(r"^\+мрп(?:\s|$)", flags=re.IGNORECASE))
)
async def set_rp_command(msg: Message):
    """Команда: +мрп {команда} {enter} {эмодзи} {enter} {действие}"""
    lines = msg.text.splitlines()

    if len(lines) < 3 or not lines[0].lower().startswith("+мрп "):
        await msg.reply("❌ Параметры команды указаны неверно.")
        return

    command = lines[0][5:].strip().lower()
    emoji_text = lines[1].strip()
    action = "\n".join(lines[2:]).strip()

    if not command or not emoji_text or not action:
        await msg.reply("❌ Команда, эмодзи и действие не могут быть пустыми.")
        return
    if len(command) > 50:
        await msg.reply("❌ Слишком длинная команда (макс 50 символов)")
        return
    elif len(action) > 200:
        await msg.reply("❌ Слишком длинное действие (макс 200 символов)")
        return

    emojis = emoji.emoji_list(emoji_text)
    only_emojis_up_to_3 = len(emojis) <= 3 and emoji_text == ''.join(e['emoji'] for e in emojis)

    if not only_emojis_up_to_3:
        await msg.reply("❌ Эмодзи указано неверно. Используйте не больше троих эмодзи.")
        return
    
    max_cmd = MAX_RP_COMMANDS_IN_CHAT_PER_USER
    count = await count_user_commands(int(msg.chat.id), int(msg.from_user.id))
    if count >= max_cmd:
        await msg.reply(f"❌ Превышено максимальное количество РП команд на пользователя в чате ({max_cmd}).")
        return

    await upsert_command(int(msg.chat.id), int(msg.from_user.id), command, emoji_text, action)
    await msg.reply(f"🎭 Команда добавлена успешно")

@router.message(
    (F.text.regexp(r"^-мрп(?:\s|$)", flags=re.IGNORECASE))
)
async def unset_rp_command(msg: Message):
    """Команда: -мрп {команда}"""
    pattern = re.compile(
        r"^-мрп\s+(?P<command>.+)$",
        re.IGNORECASE
    )

    match = pattern.match(msg.text)
    if not match:
        await msg.reply("❌ Параметры команды указаны неверно.")
        return
    command = match.group("command").strip().lower()

    if not command:
        await msg.reply("❌ Команда не может быть пустой.")
        return

    result = await delete_rp_command(int(msg.chat.id), int(msg.from_user.id), command)
    
    if result:
        await msg.reply(f"🎭 Команда удалена успешно")
    else:
        await msg.reply(f"❌ Команда не найдена")
