import re
import emoji
from aiogram import Router, F
from aiogram.types import Message

from config import MAX_RP_COMMANDS_IN_CHAT_PER_USER
from db.users.rp_commands import count_user_commands, upsert_command, delete_rp_command, get_user_rp_commands, export_rp_commands

router = Router(name="personal_rp_commands")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(
    F.text.regexp(r"^мрп список(?:\s|$)", flags=re.IGNORECASE) |
    F.text.regexp(r"^мрп лист(?:\s|$)", flags=re.IGNORECASE)
)
async def show_rp_commands_handler(msg: Message):
    """Команда: мрп список"""
    commands = await get_user_rp_commands(int(msg.chat.id), int(msg.from_user.id))
    if not commands:
        await msg.reply("📜 Кастомные RP-команды отсутствуют.")
        return
    
    lines = ["📜 Кастомные RP-команды:\n"]
    lines.append("<blockquote expandable>")
    
    for command, template in commands.items():
        # Разделяем эмодзи и остальной текст, если в шаблоне есть "•"
        if "•" in template:
            emoji, action = template.split("•", 1)
            emoji = emoji.strip()
            action = action.strip()
        else:
            # Если формат другой, оставляем всё как action
            emoji = ""
            action = template.strip()
        
        lines.append(f"{command} {emoji} —> {action}")
    lines.append("</blockquote>\n")

    lines.append(f"Всего: {len(commands)}")
    await msg.reply("\n".join(lines), parse_mode="HTML")

@router.message(
    F.text.regexp(r"^мрп экспорт(?:\s|$)", flags=re.IGNORECASE)
)
async def export_rp_commands_handler(msg: Message):
    # Упрощаем получение ID из текста
    parts = msg.text.split()

    # Мы не используем .isdigit, т.к chat_id часто начинаются с "-"
    try:
        export_id = int(parts[2])
    except (IndexError, ValueError):
        export_id =  None

    if export_id is not None:
        user_id = msg.from_user.id
        current_chat_id = msg.chat.id
        source_chat_id = int(export_id)

        # Если пользователь пытается экспортировать из этого же чата
        if source_chat_id == current_chat_id:
            return await msg.reply("❌ Нельзя экспортировать команды в этот же чат.")

        # Вызываем "умную" функцию экспорта
        added_cmds = await export_rp_commands(
            source_chat_id, 
            user_id, 
            current_chat_id, 
            MAX_RP_COMMANDS_IN_CHAT_PER_USER
        )

        if added_cmds:
            # Склеиваем первые 5 команд для примера в сообщении
            cmd_list = ", ".join(added_cmds[:5])
            more = f" и еще {len(added_cmds) - 5}..." if len(added_cmds) > 5 else ""
            
            await msg.reply(
                f"✅ <b>Экспорт завершен!</b>\n"
                f"Добавлено новых команд: <b>{len(added_cmds)}</b>\n"
                f"Список: <code>{cmd_list}{more}</code>",
                parse_mode="HTML"
            )
        else:
            await msg.reply(
                "❌ <b>Экспорт не удался</b>\n\n"
                "Возможные причины:\n"
                "1. Команды из того чата уже добавлены.\n"
                "2. Будет превышен лимит команд в этом чате.\n"
                "3. У вас нет команд в указанном чате.",
                parse_mode="HTML"
            )
    
    else:
        # Если ввели просто "мрп экспорт" — даем инструкцию
        await msg.reply(
            f"Чтобы перенести команды из этого чата в другой, введите там:\n"
            f"<code>мрп экспорт {msg.chat.id}</code>", 
            parse_mode="HTML"
        )

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
