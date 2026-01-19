from typing import ClassVar

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

class UserInfo(CallbackData, prefix="qd"):
        action: ClassVar[str] = "user_info"
        secondary_action: str
        user_id: int

async def get_user_info_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="👩‍👩‍👦 Семья",
            callback_data=UserInfo(secondary_action = "family", user_id = user_id).pack()
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🏆 Награды",
            callback_data=UserInfo(secondary_action = "awards", user_id = user_id).pack()
        ),
        InlineKeyboardButton(
            text="⚠️ Варны",
            callback_data=UserInfo(secondary_action = "warnings", user_id = user_id).pack()
        ),
    )

    return builder.as_markup()
