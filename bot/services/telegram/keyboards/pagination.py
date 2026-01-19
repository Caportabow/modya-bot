from typing import Optional

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

# -- Pagination --
class Pagination(CallbackData, prefix="pn"):
        subject: str
        page: int
        query: Optional[int]
        with_back_button: bool
        is_back_button: bool

async def get_pagination_keyboard(subject: str, query: Optional[int], next_page: Optional[int] = None, prev_page: Optional[int] = None, back_button_active: bool = False):
    builder = InlineKeyboardBuilder()
    row_buttons = []

    if prev_page is not None:
        row_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Пред.",
                callback_data=Pagination(subject=subject, query=query, page=prev_page, with_back_button=back_button_active, is_back_button=False).pack()
            )
        )

    if next_page is not None:
        row_buttons.append(
            InlineKeyboardButton(
                text="След. ➡️",
                callback_data=Pagination(subject=subject, query=query, page=next_page, with_back_button=back_button_active, is_back_button=False).pack()
            )
        )

    if row_buttons:
        builder.row(*row_buttons)
    
    if back_button_active:
        builder.row(
            InlineKeyboardButton(
                text="Назад",
                callback_data=Pagination(subject=subject, query=query, page=0, with_back_button=back_button_active, is_back_button=True).pack()
            )
        )
    
    return builder.as_markup()
