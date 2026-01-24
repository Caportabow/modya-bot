from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import User, InlineKeyboardMarkup, BufferedInputFile

from services.telegram.user_mention import mention_user
from db.marriages import get_user_marriage
from db.marriages.families import get_family_tree_data, is_child, is_ancestor

from services.web.families import make_family_tree
from services.telegram.keyboards.pagination import get_pagination_keyboard


async def generate_family_tree_msg(bot: Bot, chat_id: int, user_entity: User, with_back_button: bool = False) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup], Optional[BufferedInputFile]]:
    user_id = int(user_entity.id)
    family_tree_data = await get_family_tree_data(chat_id, user_id)

    if not family_tree_data or len(family_tree_data) == 0:
        return None, None, None
    
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=user_entity)
    family_tree_bytes = await make_family_tree(family_tree_data)

    photo = BufferedInputFile(family_tree_bytes, filename="family_tree.jpeg")
    keyboard = await get_pagination_keyboard(
        subject = "family", query=user_id, next_page=None,
        prev_page=None, back_button_active=with_back_button
    )
    return f"🌳 Семейное древо {mention}", keyboard, photo

async def can_become_parent(
    chat_id: int,
    parent_user_id: int,
    child_user_id: int,
) -> Tuple[bool, Optional[str]]:
    marriage = await get_user_marriage(chat_id, parent_user_id)
    if not marriage:
        return False, f"❌ Вы должны быть в браке, чтобы стать родителем."
    
    if child_user_id in marriage['participants']:
        return False, f"❌ Вы не можете стать родителем для своего супруга."

    child = await is_child(chat_id, child_user_id)
    if child:
        return False, f"❌ Этот пользователь уже чей-то ребёнок."
    
    for spouse in marriage['participants']:
        ancestor = await is_ancestor(chat_id, child_user_id, spouse)
        if ancestor:
            return False, f"❌ Вы не можете стать родителем своего предка."
    
    return True, None
