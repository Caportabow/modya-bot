from typing import ClassVar

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

class QuoteDelition(CallbackData, prefix="qd"):
        action: ClassVar[str] = "delete_quote"

async def get_quote_delition_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=QuoteDelition().pack()
        ),
    )

    return builder.as_markup()
