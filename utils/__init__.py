from db import get_nickname, get_uid

async def mention_user(
        bot = None,
        user_entity = None, chat_id: int | None = None,
        user_id: int | None = None, user_username: str | None = None
        ):
    if not user_entity:
        if not user_id:
            user_id = await get_uid(chat_id=chat_id, username=user_username)
            if not user_id:
                return f"@{user_username}" or "неизвестный"
        
        user_member = await bot.get_chat_member(chat_id, int(user_id))
        user_entity = user_member.user
    else:
        user_id = user_entity.id
    
    user_nickname = await get_nickname(chat_id=chat_id, uid=int(user_id))

    mention = user_entity.mention_html(name=user_nickname)
    return mention

async def parse_user_mention(
        msg,
    ):
    """Парсит пользователя из сообщения."""
    user = None
    for entity in msg.entities:
        if entity.type == "text_mention" and entity.user:
            user = entity.user
            break
        elif entity.type == "mention":
            username = msg.text[entity.offset + 1: entity.offset + entity.length]
            try:
                uid = await get_uid(int(msg.chat.id), username)
                if uid: user = await bot.get_chat_member(chat_id=msg.chat.id, user_id=uid)
                if user:
                    user = user.user
                    break
            except:
                pass
    return user

async def is_admin(bot, chat_id: int, user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором чата."""
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return (
            member.status == "creator" or
            (member.status == "administrator" and member.can_restrict_members)
        )
    except:
        return False
    