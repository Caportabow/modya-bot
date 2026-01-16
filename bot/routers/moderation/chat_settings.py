import re
from aiogram import Router, F
from aiogram.types import Message
from datetime import timedelta, datetime, time

from db.chats.settings import set_max_warns, set_cleaning_min_messages, set_cleaning_max_inactive, set_cleaning_eligibility_duration, set_cleaning_lookback, enable_auto_cleaning, disable_auto_cleaning, get_all_settings
from db.chats.cleaning import check_cleanability
from utils.telegram.users import is_admin
from utils.time import DurationParser, TimedeltaFormatter

router = Router(name="chat_settings")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(
    F.text.regexp(r"^\.\s*лимит варнов(?:\s|$)", flags=re.IGNORECASE)
)
async def set_max_warns_handler(msg: Message):
    """Команда: .лимит варнов {кол-во}"""
    match = re.search(
        r"^\.\s*лимит варнов\s+(\d+)\s*$",
        str(msg.text),
        flags=re.IGNORECASE
    )
    if not match:
        await msg.reply("❌ Укажите корректное число")
        return

    max_warns = int(match.group(1))

    if max_warns < 1:
        await msg.reply("❌ Минимальный лимит варнов — 1")
        return
    elif max_warns > 100:
        await msg.reply("❌ Максимальный лимит варнов — 100")
        return

    access = await is_admin(bot=msg.bot, chat_id=int(msg.chat.id), user_id=int(msg.from_user.id))
    if not access:
        await msg.reply("❌ Только администраторы могут изменять лимит варнов")
        return

    await set_max_warns(int(msg.chat.id), max_warns)
    await msg.reply(f"📛 Новое максимальное кол-во варнов: {max_warns}")

@router.message(
    F.text.regexp(r"^\.\s*норма(?:\s|$)", flags=re.IGNORECASE)
)
async def set_cleaning_min_messages_handler(msg: Message):
    """Команда: .норма {кол-во}"""
    match = re.search(
        r"^\.\s*норма\s+(\d+)\s*$",
        str(msg.text),
        flags=re.IGNORECASE
    )
    if not match:
        await msg.reply("❌ Укажите корректное число")
        return
    
    min_messages = int(match.group(1))

    if min_messages < 1:
        await msg.reply("❌ Минимальная норма — 1 сообщ.")
        return

    access = await is_admin(bot=msg.bot, chat_id=int(msg.chat.id), user_id=int(msg.from_user.id))
    if not access:
        await msg.reply("❌ Только администраторы могут изменять норму")
        return

    await set_cleaning_min_messages(int(msg.chat.id), min_messages)
    await msg.reply(f"📛 Новая норма: {min_messages}")

@router.message(
    F.text.regexp(r"^\.\s*неактив(?:\s|$)", flags=re.IGNORECASE)
)
async def set_cleaning_max_inactive_handler(msg: Message):
    """Команда: .неактив {период}"""
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply("❌ Укажите максимальный период неактивности")
        return
    
    max_inactive = DurationParser().parse(text=parts[1].strip())
    if not max_inactive:
        await msg.reply("❌ Укажите корректный период")
        return

    access = await is_admin(bot=msg.bot, chat_id=int(msg.chat.id), user_id=int(msg.from_user.id))
    if not access:
        await msg.reply("❌ Только администраторы могут изменять макс. период неактивности")
        return

    await set_cleaning_max_inactive(int(msg.chat.id), max_inactive)
    await msg.reply(f"📛 Новый макс. период неактивности: {TimedeltaFormatter().format(max_inactive, suffix="none")}")

@router.message(
    F.text.regexp(r"^\.\s*возраст нью(?:\s|$)", flags=re.IGNORECASE)
)
async def set_cleaning_eligibility_duration_handler(msg: Message):
    """Команда: .возраст нью {период}"""
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.reply("❌ Укажите максимальный возраст нью")
        return
    
    eligibility_duration = DurationParser().parse(text=parts[2].strip())
    if not eligibility_duration:
        await msg.reply("❌ Укажите корректный период")
        return

    access = await is_admin(bot=msg.bot, chat_id=int(msg.chat.id), user_id=int(msg.from_user.id))
    if not access:
        await msg.reply("❌ Только администраторы могут изменять макс. возраст нью")
        return

    await set_cleaning_eligibility_duration(int(msg.chat.id), eligibility_duration)
    await msg.reply(f"📛 Новый макс. возраст нью: {TimedeltaFormatter().format(eligibility_duration, suffix="none")}")

@router.message(
    F.text.regexp(r"^\.\s*период чистки(?:\s|$)", flags=re.IGNORECASE)
)
async def set_cleaning_lookback_handler(msg: Message):
    """Команда: .период чистки {период}"""
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 3:
        await msg.reply("❌ Укажите период чистки")
        return
    
    cleaning_lookback = DurationParser().parse(text=parts[2].strip())
    if not cleaning_lookback:
        await msg.reply("❌ Укажите корректный период")
        return

    access = await is_admin(bot=msg.bot, chat_id=int(msg.chat.id), user_id=int(msg.from_user.id))
    if not access:
        await msg.reply("❌ Только администраторы могут изменять период чистки")
        return

    await set_cleaning_lookback(int(msg.chat.id), cleaning_lookback)
    await msg.reply(f"📛 Новый период чистки: {TimedeltaFormatter().format(cleaning_lookback, suffix="none")}")

@router.message(
    F.text.regexp(r"^\.\s*авточистка(?:\s|$)", flags=re.IGNORECASE)
)
async def auto_cleaning_handler(msg: Message):
    """
    Команда: .авточистка {день недели} {время по utc}
    Или: .авточистка выключить
    """
    chat_id = int(msg.chat.id)
    access = await is_admin(bot=msg.bot, chat_id=chat_id, user_id=int(msg.from_user.id))
    if not access:
        await msg.reply("❌ Только администраторы могут включить авточистку")
        return

    # проверяем, не выключить ли
    if re.search(r"\bвыключить\b", str(msg.text), re.IGNORECASE):
        await msg.reply("📛 Авточистка успешно выключена.")
        await disable_auto_cleaning(chat_id)
        return

    # ищем день недели + время в формате HH:MM
    m = re.search(
        r"\b(понедельник|вторник|среда|четверг|пятница|субота|суббота|воскресенье)\b\s+([0-2]?\d:[0-5]\d)",
        str(msg.text),
        re.IGNORECASE,
    )
    if not m:
        await msg.reply("❌ Некорректный формат")
        return

    day_str, time_str = m.groups()
    DAYS_MAP = {
        "понедельник": 1,
        "вторник": 2,
        "среда": 3,
        "четверг": 4,
        "пятница": 5,
        "субота": 6,
        "суббота": 6,  # иногда пишут по-разному
        "воскресенье": 7,
    }
    day = DAYS_MAP[day_str.lower()]

    # преобразуем в объект времени, пригодный для PostgreSQL TIME
    hour, minute = map(int, time_str.split(":"))
    pg_time = time(hour, minute)  # хранить как TIME


    # проверяем, хватает ли нам данных чтобы включить чистку
    ability = await check_cleanability(chat_id)
    if not ability:
        await msg.reply("❗️ Чистка недоступна. Настройки чистки отсутствуют или заполнены не полностью.", parse_mode="HTML")
        return
    
    def time_until_next_cleaning(day: int, cleaning_time: time) -> timedelta:
        now = datetime.now()
        
        # строим datetime для ближайшего дня недели с нужным временем
        days_ahead = day - now.isoweekday()
        if days_ahead < 0 or (days_ahead == 0 and cleaning_time <= now.time()):
            # если день прошёл или это сегодня, но время уже прошло → переносим на следующую неделю
            days_ahead += 7

        next_cleaning = datetime.combine(
            now.date() + timedelta(days=days_ahead),
            cleaning_time
        )

        return next_cleaning - now
    
    await enable_auto_cleaning(chat_id, day, pg_time)
    await msg.reply(f"📛 Авточистка успешно включена\n⏳ Cледующая чистка через {TimedeltaFormatter.format(time_until_next_cleaning(day, pg_time), suffix="none")}")


@router.message(
    F.text.startswith("/settings") |
    F.text.regexp(r"^\.\s*настройки(?:\s|$)", flags=re.IGNORECASE)
)
async def show_settings_handler(msg: Message):
    chat_id = int(msg.chat.id)
    settings = await get_all_settings(chat_id)

    if not settings:
        return
    max_warns = settings["max_warns"] or 3
    norm = f"{settings["cleaning_min_messages"]} сообщ." if settings["cleaning_min_messages"] else "не установлена"
    inactive = TimedeltaFormatter.format(settings["cleaning_max_inactive"], suffix="none") if settings["cleaning_max_inactive"] else "не установлен"
    new_member_age = TimedeltaFormatter.format(settings["cleaning_eligibility_duration"], suffix="none") if settings["cleaning_eligibility_duration"] else "не установлен"
    lookback = TimedeltaFormatter.format(settings["cleaning_lookback"], suffix="none") if settings["cleaning_lookback"] else "не установлен"

    ISO_MAP = { 1: "каждый понедельник", 2: "каждый вторник", 3: "каждую среду",
        4: "каждый четверг", 5: "каждую пятницу", 6: "каждую субботу", 7: "каждое воскресенье",
    }
    autoclean = f"{ISO_MAP[int(settings["cleaning_day_of_week"])]} в {settings["cleaning_time"].strftime("%H:%M")}" if settings["autoclean_enabled"] else "выключена"

    ans = "⚙️ Настройки чата:\n\n"
    ans += "1. 🧹 Чистка\n"
    ans += "<blockquote expandable>"
    ans += f"Авточистка - {autoclean}\n"
    ans += f"Норма - {norm}\n"
    ans += f"Макс. неактив - {inactive}\n"
    ans += f"Мин. возраст нью для участия в чистке - {new_member_age}\n"
    ans += f"Период чистки - {lookback}"
    ans += "</blockquote>\n\n"
    ans += "2. 🌀 Остальное\n"
    ans += "<blockquote expandable>"
    ans += f"Макс. кол-во варнов - {max_warns}"
    ans += "</blockquote>\n\n"

    await msg.reply(ans, parse_mode="HTML")
