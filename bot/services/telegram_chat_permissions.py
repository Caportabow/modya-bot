from aiogram import Bot
from services.telegram.chat_member import get_chat_member

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    member = await get_chat_member(bot, chat_id, user_id)

    if not member:
        return False

    if member.status == "creator":
        return True

    return (
        member.status == "administrator"
        and member.can_restrict_members
    )

async def is_creator(bot: Bot, chat_id: int, user_id: int) -> bool:
    member = await get_chat_member(bot, chat_id, user_id)
    return bool(member and member.status == "creator")
