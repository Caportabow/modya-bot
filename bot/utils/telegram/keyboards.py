from datetime import timedelta
from typing import ClassVar, Optional

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

# сериализация timedelta -> int
def serialize_timedelta(delta: timedelta) -> int:
    return int(delta.total_seconds())
# десериализация int -> timedelta
def deserialize_timedelta(seconds: int) -> timedelta:
    return timedelta(seconds=seconds)

# -- Rests --
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


# -- Marriages --
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


# -- Families --
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


# -- Quotes --
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


# -- User Info --
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

# -- Pagination --
class Pagination(CallbackData, prefix="pn"):
        subject: str
        page: int
        query: Optional[int]

async def get_pagination_keyboard(subject: str, query: Optional[int], next_page: Optional[int] = None, prev_page: Optional[int] = None):
    builder = InlineKeyboardBuilder()
    row_buttons = []

    if prev_page is not None:
        row_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Пред.",
                callback_data=Pagination(subject=subject, query=query, page=prev_page).pack()
            )
        )

    if next_page is not None:
        row_buttons.append(
            InlineKeyboardButton(
                text="След. ➡️",
                callback_data=Pagination(subject=subject, query=query, page=next_page).pack()
            )
        )

    if row_buttons:
        builder.row(*row_buttons)
    
    return builder.as_markup()
