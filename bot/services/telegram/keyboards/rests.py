from datetime import timedelta
from typing import ClassVar, Optional

from utils.time import serialize_timedelta
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

class RestRequest(CallbackData, prefix="rr"):
        action: ClassVar[str] = "rest_request"
        response: str
        delta: Optional[int] = None

async def get_rest_request_keyboard(delta: timedelta):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить",
            callback_data=RestRequest(response = "accept", delta = serialize_timedelta(delta)).pack()
        ),
        InlineKeyboardButton(
            text="❌ Отказать",
            callback_data=RestRequest(response = "decline").pack()
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="↩️ Отозвать",
            callback_data=RestRequest(response = "retire").pack()
        ),
    )

    return builder.as_markup()
