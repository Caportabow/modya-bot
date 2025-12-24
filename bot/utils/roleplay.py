from aiogram import Bot, types
from utils.telegram.users import mention_user
from config import RP_COMMANDS

def _find_command(text: str, rp_commands: dict):
    words = text.lower().split(" ")

    # Сортируем команды по количеству слов (от большего к меньшему)
    sorted_commands = sorted(rp_commands.keys(), key=lambda c: -len(c.split(" ")))

    for cmd in sorted_commands:
        cmd_words = cmd.split(" ")
        if words[:len(cmd_words)] == cmd_words:
            rest = words[len(cmd_words):]
            return rp_commands[cmd], " ".join(rest) if rest else None

    return None, None

def _find_comment(text: str):
    lines = text.splitlines()
    if not lines: return None, text
    
    head, *command = lines
    return ("\n".join(command) if command else None), head

def _find_target(text):
    words = text.split(" ")
    for i, word in enumerate(words):
        if word.startswith("@"):
            rest = words[:i] + words[i+1:]
            return word[1:] if len(word) > 1 else None, " ".join(rest) if rest else None
    return None, text

async def parse_rp_command(bot: Bot, chat_id:int, text:str, trigger_user_entity: types.User, target_user_entity: types.User | None = None, user_rp_commands: dict | None = None) -> str | None:
    comment, rest = _find_comment(text) # сначала ищем комментарий (!иначе может быть вырезан случайно)
    if not rest: return None

    target_user_username, rest = _find_target(rest) # потом цель (если есть), чтобы не делать лишних проверок
    if not rest: return None

    # Собираем список из доступных РП команд
    all_rp_commands = {**RP_COMMANDS, **(user_rp_commands or {})}

    # Наконец ищем команду
    command, rest = _find_command(rest, all_rp_commands)
    if not command:
        return None
    
    # Упоминаем юзеров
    trigger_user = await mention_user(bot=bot, chat_id=chat_id, user_entity=trigger_user_entity)
    if target_user_username:
        target_user = await mention_user(bot=bot, chat_id=chat_id, user_username=target_user_username)
    else:
        target_user = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user_entity)
    
    # Теперь собираем команду.
    argument = "" if not rest else f"{rest} "
    command = command.format(trigger=trigger_user, target=argument + target_user)
    if comment: command += f"\n💬 С комментарием: {comment}"

    return command
