from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import User, InlineKeyboardMarkup, BufferedInputFile

from db.marriages.families import get_family_tree_data

from utils.web.families import make_family_tree
from utils.telegram.keyboards import get_pagination_keyboard
from utils.telegram.users import mention_user


async def family_tree(bot: Bot, chat_id: int, user_entity: User, with_back_button: bool = False) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup], Optional[BufferedInputFile]]:
    user_id = int(user_entity.id)
    family_tree_data = await get_family_tree_data(chat_id, user_id)

    if not family_tree_data or len(family_tree_data) == 0:
        return None, None, None
    
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=user_entity)
    family_tree_bytes = await make_family_tree(family_tree_data)

    photo = BufferedInputFile(family_tree_bytes, filename="family_tree.jpeg")
    keyboard = await get_pagination_keyboard(
        subject = "family", query=None, next_page=None,
        prev_page=None, back_button_active=with_back_button
    )
    return f"🌳 Семейное древо {mention}", keyboard, photo