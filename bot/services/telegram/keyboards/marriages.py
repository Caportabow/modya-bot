from typing import ClassVar

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

class MarriageRequest(CallbackData, prefix="mr"):
        action: ClassVar[str] = "proposal"
        response: str
        trigger_user_id: int
        target_user_id: int

async def get_marriage_request_keyboard(trigger_user_id, target_user_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💍 Сказать «Да»",
            callback_data=MarriageRequest(response = "accept", trigger_user_id=trigger_user_id, target_user_id=target_user_id).pack()
        ),
        InlineKeyboardButton(
            text="💔 Отказать",
            callback_data=MarriageRequest(response = "decline", trigger_user_id=trigger_user_id, target_user_id=target_user_id).pack()
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="↩️ Отозвать",
            callback_data=MarriageRequest(response = "retire", trigger_user_id=trigger_user_id, target_user_id=target_user_id).pack()
        ),
    )

    return builder.as_markup()
