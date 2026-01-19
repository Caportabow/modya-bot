from datetime import datetime, timezone
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import User, InlineKeyboardMarkup, BufferedInputFile

from services.telegram.user_mention import mention_user
from db.users import get_uid
from db.messages import plot_user_activity
from db.messages.statistics import user_stats, get_favorite_word

from services.time_utils import TimedeltaFormatter
from services.telegram.keyboards.user_info import get_user_info_keyboard
from services.web.activity_chart import make_activity_chart

async def generate_user_info_msg(bot: Bot, chat_id: int, user_entity: User) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup], Optional[BufferedInputFile]]:
    user_id = int(user_entity.id)

    stats = await user_stats(chat_id, user_id)
    user_activity = await plot_user_activity(chat_id=chat_id, user_id=user_id)
    img = await make_activity_chart(user_activity)
    fav_word = await get_favorite_word(chat_id, user_id)
    if not stats or not img:
        return None, None, None
    
    now = datetime.now(timezone.utc)
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=user_entity)

    ans = f"👤 Это пользователь {mention}\n\n"
    if fav_word:
        fav_word_count = fav_word["count"]
        fav_word = fav_word["word"]

        fav_user_id = await get_uid(chat_id, fav_word)

        if not fav_user_id:
            ans += f"Любимое слово: {fav_word} ({fav_word_count} р.)\n"
        else:
            fav_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=int(fav_user_id))
            ans += f"Любимый юзер: {fav_user_mention} ({fav_word_count} р.)\n"
    else: ans += f"Любимое слово: (данных недостаточно)\n"
    ans += f"Дебют: {stats["first_seen"]:%d.%m.%Y} ({TimedeltaFormatter.format(now - stats["first_seen"])})\n"
    ans += f"Последний актив: { TimedeltaFormatter.format(now - stats["last_active"])}\n"

    if stats["rest"]:
        ans += f"Рест: до {stats["rest"]:%d.%m.%Y} (еще {TimedeltaFormatter.format(stats["rest"] - now, suffix="none")})\n"
    else:
        ans += f"Рест: (не активен)\n"

    ans += f"Актив (24ч|7дн|30дн|∞): {stats["activity"]["day_count"]} | {stats["activity"]["week_count"]} | {stats["activity"]["month_count"]} | {stats["activity"]["total"]}\n"
    uploaded_img = BufferedInputFile(img, filename="stats.png")
    keyboard = await get_user_info_keyboard(user_id)

    return ans, keyboard, uploaded_img