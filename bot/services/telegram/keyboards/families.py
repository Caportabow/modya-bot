from typing import ClassVar, Optional

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

class AdoptionRequest(CallbackData, prefix="ar"):
        action: ClassVar[str] = "adoption"
        response: str
        trigger_user_id: int
        target_user_id: int

async def get_adoption_request_keyboard(trigger_user_id, target_user_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💝 Вступить",
            callback_data=AdoptionRequest(response = "accept", trigger_user_id=trigger_user_id, target_user_id=target_user_id).pack()
        ),
        InlineKeyboardButton(
            text="😔 Отказать",
            callback_data=AdoptionRequest(response = "decline", trigger_user_id=trigger_user_id, target_user_id=target_user_id).pack()
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="↩️ Отозвать",
            callback_data=AdoptionRequest(response = "retire", trigger_user_id=trigger_user_id, target_user_id=target_user_id).pack()
        ),
    )

    return builder.as_markup()
