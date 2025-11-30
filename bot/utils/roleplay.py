from aiogram import Bot
from .telegram.users import mention_user
from config import RP_COMMANDS

def _find_command(text, rp_commands):
    words = text.split(" ")

    for i in range(1, len(words) + 1):
        candidate = " ".join(words[:i]).lower()
        if candidate in rp_commands:
            words = words[i:]
            return rp_commands[candidate], " ".join(words) if words else None
    
    return None, None

def _find_comment(text: str):
    lines = text.splitlines()
    head, *command = lines
    return ("\n".join(command) if command else None), head

def _find_target(text):
    words = text.split(" ")
    for i, word in enumerate(words):
        if word.startswith("@"):
            rest = words[:i] + words[i+1:]
            return word[1:] if len(word) > 1 else None, " ".join(rest) if rest else None
    return None, text


async def parse_rp_command(bot: Bot, chat_id:int, text:str, trigger_user_entity, target_user_entity = None):
    comment, rest = _find_comment(text) # сначала ищем комментарий (!иначе может быть вырезан случайно)
    if not rest: return None

    target_user_username, rest = _find_target(rest) # потом цель (если есть), чтобы не делать лишних проверок
    if not rest: return None

    # Наконец ищем команду
    command, rest = _find_command(rest, RP_COMMANDS)
    if not command:
        return None
    
    # Упоминаем юзеров
    trigger_user = await mention_user(bot=bot, chat_id=chat_id, user_entity=trigger_user_entity)
    if target_user_username:
        target_user = await mention_user(bot=bot, chat_id=chat_id, user_username=target_user_username)
    else:
        target_user = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user_entity)
    
    # Теперь собираем команду.
    command = command.format(trigger=trigger_user, target=target_user)
    if rest: command += " " + rest
    if comment: command += f"\n💬 С комментарием: {comment}"
    #if interraction_success: command += f"\n💖 Крепкость брака увеличилась"

    return command
