import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from middlewares.maintenance import MaintenanceMiddleware
from services.messaging.leaderboard import generate_leaderboard_msg

from services.telegram.keyboards.pagination import Pagination
from services.time_utils import DurationParser, deserialize_timedelta

router = Router(name="leaderboard")
router.message.middleware(MaintenanceMiddleware())
router.callback_query.middleware(MaintenanceMiddleware())
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(
    F.text.regexp(r"^топ(?:\s|$)", flags=re.IGNORECASE)
)
async def stats_handler(msg: Message):
    """Команда: топ {период}"""
    bot = msg.bot
    parts = msg.text.split(maxsplit=1)

    duration = None
    if len(parts) > 1:
        duration = DurationParser.parse(parts[1].strip())

        if not duration:
            # аргумент не задан или пользователь указал "навсегда"
            if not DurationParser.parse_forever(parts[1].strip()):
                # команда вероятно сработала случайно, останавливаем обработку
                return

    text, keyboard = await generate_leaderboard_msg(bot, int(msg.chat.id), page=1, duration=duration)
    if not text:
        await msg.reply("❌ Недостаточно информации.")
        return

    await msg.reply(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(Pagination.filter(F.subject == "leaderboard"))
async def leaderboard_pagination_handler(callback: CallbackQuery, callback_data: Pagination):
    if callback_data.query is not None:
        duration = deserialize_timedelta(callback_data.query)
    else: duration = None

    text, keyboard = await generate_leaderboard_msg(callback.bot, callback.message.chat.id, callback_data.page, duration)

    if text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer("") # пустой ответ, чтобы убрать "часики"
    
    else:
        await callback.answer(text="❌ Неизвестная ошибка.", show_alert=True)
