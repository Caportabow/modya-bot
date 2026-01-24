import random
from datetime import datetime, timezone
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from services.telegram.user_mention import mention_user
from db.marriages import get_marriages, get_user_marriage, delete_marriage
from db.marriages.families import incest_cycle

from services.time_utils import TimedeltaFormatter
from services.telegram.keyboards.pagination import get_pagination_keyboard

async def generate_all_marriages_msg(bot: Bot, chat_id: int, page: int) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    data = await get_marriages(chat_id, page)
    if not data:
        return None, None

    marriages = data["data"]
    now = datetime.now(timezone.utc)
    ans = f"💕 Пары нашего чата:\n\n"

    ans += "<blockquote expandable>"
    for i, m in enumerate(marriages):
        mention_1 = await mention_user(bot=bot, chat_id=chat_id, user_id=int(m["participants"][0]))
        mention_2 = await mention_user(bot=bot, chat_id=chat_id, user_id=int(m["participants"][1]))
        
        date = f"{m['date']:%d.%m.%Y} ({TimedeltaFormatter.format(now - m['date'], suffix='none')})"
        line = f"• {mention_1} & {mention_2}\n   └ Вместе с {date}\n\n"
        
        ans += line
    ans += "</blockquote>"

    pagination = data["pagination"]
    keyboard = await get_pagination_keyboard(
        subject = "all_marriages", query=None, next_page=pagination["next_page"],
        prev_page=pagination["prev_page"]
    )

    return ans, keyboard

async def can_get_married(bot: Bot, chat_id: int, user_id: int, potential_partner_id: int) -> Tuple[bool, Optional[str]]:
    """Проверяем может ли пара поженится."""
    marriage = await get_user_marriage(chat_id, user_id)

    if not marriage: # Юзер не женат
        marriage = await get_user_marriage(chat_id, potential_partner_id) # Брак потенциального партнёра

        if not marriage: # Оба юзера не женаты
            cycle = await incest_cycle(chat_id, user_id, potential_partner_id)
            if not cycle: # Потенциальная пара не связана вертикальным родством
                return True, None
            
            # Потенциальная пара связана вертикальным родством
            return False, "❌ Вы не можете заключить брак со своим предком."
        
        # Один из партнёров женат
        potential_partner_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=potential_partner_id)
        return False, f"❌ {potential_partner_mention} уже в браке."

    # Юзер женат
    if potential_partner_id in marriage["participants"]: # Юзер и потенциальный партнёр и так женаты
        return False, f"❌ Вы и так в браке."

    # Юзер пытается изменить своему партнёру
    partner_id = marriage["participants"][0] if marriage["participants"][0] != user_id else marriage["participants"][1]
    partner_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=partner_id)
    random_phrases = ["потяните сильнее за поводок пожалуйста",
                        "error 404: верность не найдена",
                        "ваше уплыло", "ваш партнёр сбежал, заберите пожалуйста"]
    return False, f"❗️ {partner_mention}, {random.choice(random_phrases)}!"

async def delete_marriage_and_notify(bot: Bot, chat_id: int, user_id: int, left_chat: bool = False) -> Optional[str]:
    marriage = await get_user_marriage(chat_id, user_id)
    if not marriage:
        # Уведомляем что брака не было только если юзер хотел развестись умышленно
        return "❌ Вы не женаты." if not left_chat else None
        
    # Удаляем брак
    await delete_marriage(chat_id, marriage_id=marriage["marriage_id"])
   
    # Уведомляем партнёра и детей в одном сообщении
    partner_id = marriage["participants"][0] if marriage["participants"][0] != user_id else marriage["participants"][1]
    partner_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=partner_id)
    children = marriage["children"]

    children_mentions = []
    if children:
        for child_id in children:
            child_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=child_id)
            children_mentions.append(child_mention)

    # Формируем текст сообщения
    reason = "покинул чат" if left_chat else "подал на развод"
    text = f"💔 {partner_mention}, мне очень жаль, ваш супруг {reason}. Семейная жизнь окончена."

    if len(children_mentions):
        text += "\n\n🥀 Один из родителей покинул семью. Ваши дети осиротели:\n"
        for mention in children_mentions:
            text += f" - {mention}\n"

    return text
