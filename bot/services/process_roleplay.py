import re
from aiogram import Bot, html
from aiogram.types import User
from typing import Optional

from config import RP_COMMANDS
from services.telegram.user_mention import mention_user

async def parse_rp_command(
    bot: Bot, 
    chat_id: int, 
    text: str, 
    trigger_user_entity: User, 
    target_user_entity: Optional[User],
    user_rp_commands: dict | None = None
) -> str | None:
    """
    Парсит РП команду.
    Логика:
    1. Отделяем комментарий.
    2. Ищем команду в начале строки (Regex).
    3. Всё остальное — аргумент действия.
    4. Цель берется строго из target_user_entity.
    """

    # 1. Разделяем текст и комментарий (по первой новой строке)
    parts = text.split('\n', maxsplit=1)
    main_line = parts[0].strip()
    comment_text = parts[1].strip() if len(parts) > 1 else None

    if not main_line:
        return None

    # 2. Собираем и сортируем команды
    # Объединяем глобальные и пользовательские команды
    # Если user_rp_commands is None, используем {}
    all_commands = {**RP_COMMANDS, **(user_rp_commands or {})}
    
    if not all_commands:
        return None

    # Сортируем по длине (от длинных к коротким), чтобы "поцеловать" не сработало раньше "жарко поцеловать"
    # Экранируем команды (re.escape), чтобы спецсимволы в командах не ломали regex
    sorted_keys = sorted(all_commands.keys(), key=len, reverse=True)
    escaped_keys = [re.escape(cmd) for cmd in sorted_keys]

    # 3. Строим Regex: ^(cmd1|cmd2|cmd3)(?:\s+|$)(.*)
    # ^             - начало строки
    # (cmd1|cmd2)   - одна из команд (группа 1)
    # (?:\s+|$)     - после команды должен быть пробел ИЛИ конец строки (чтобы чмок не сработало на чмокнуть)
    # (.*)          - всё остальное (аргумент) (группа 2)
    pattern = re.compile(rf"^({'|'.join(escaped_keys)})(?:\s+|$)(.*)", re.IGNORECASE | re.DOTALL)

    match = pattern.match(main_line)
    
    if not match:
        return None

    # Извлекаем данные из Regex
    # Так как мы делали re.IGNORECASE, то match.group(1) вернет текст ИЗ СООБЩЕНИЯ (например "поцеловать").
    # Нам нужно найти оригинальный ключ в словаре.
    command_from_text = match.group(1).lower()
    action_argument = match.group(2).strip() # Аргумент (например "крепко")

    # Получаем шаблон. Пытаемся найти по нижнему регистру.
    response_template: str = all_commands.get(command_from_text, "")
    if not len(response_template):
        return None

    # 4. Формируем ссылки
    trigger_link = await mention_user(bot=bot, chat_id=chat_id, user_entity=trigger_user_entity)
    if target_user_entity:
        target_link = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user_entity)
    else: target_link = "себя"

    # 5. Сборка аргумента
    # Если аргумент есть, добавляем пробел после него перед целью
    final_argument = f"{action_argument} " if action_argument else ""

    # 6. Финальное форматирование
    result_text = response_template.format(
        trigger=trigger_link,
        target=f"{final_argument}{target_link}"
    )

    if comment_text:
        safe_comment = html.quote(comment_text) # Важно: комментарий надо обезопасить от HTML инъекций
        result_text += f"\n💬 С комментарием: {safe_comment}"

    return result_text
