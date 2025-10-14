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
