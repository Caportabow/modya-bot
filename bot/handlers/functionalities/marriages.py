import re
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, InlineKeyboardButton

from utils.time import TimedeltaFormatter

from utils.telegram.message_templates import check_marriage_loyality, delete_marriage_and_notify, family_tree
from utils.telegram.users import mention_user_with_delay, parse_user_mention, mention_user
from config import MARRIAGES_PICTURE_ID, MAX_MESSAGE_LENGTH
from db.marriages import get_marriages, get_user_marriage
from db.marriages.families import check_adoption_possibility, is_parent, is_child, abandon, incest_cycle

router = Router(name="marriages")


@router.message((F.text.lower().startswith("браки")) & (F.chat.type.in_(["group", "supergroup"])))
async def all_marriages_handler(msg: Message):
    """Команда: браки"""
    bot = msg.bot
    chat_id = int(msg.chat.id)  
    
    marriages = await get_marriages(chat_id)
    if not marriages or len(marriages) == 0:
        await msg.reply("❌ В этом чате нет браков.")
        return
    
    now = datetime.now(timezone.utc)
    ans_header = f"💕 Пары нашего чата:\n\n"
    ans = ans_header

    for i, m in enumerate(marriages):
        mention_1 = await mention_user_with_delay(bot=bot, chat_id=chat_id, user_id=int(m["participants"][0]))
        mention_2 = await mention_user_with_delay(bot=bot, chat_id=chat_id, user_id=int(m["participants"][1]))
        
        date = f"{m['date']:%d.%m.%Y} ({TimedeltaFormatter.format(now - m['date'])})"
        line = f"▫️ {mention_1} & {mention_2}\n   └ Вместе с {date}\n\n"

        # если добавление строки превысит лимит — отправляем текущее сообщение и начинаем новое
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            await msg.reply_photo(photo=MARRIAGES_PICTURE_ID, caption=ans, parse_mode="HTML")
            ans = ans_header  # сбрасываем накопленное сообщение
        
        ans += line
    
    # добавляем остаток, если есть
    if ans.strip():
        await msg.reply_photo(photo=MARRIAGES_PICTURE_ID, caption=ans, parse_mode="HTML")

@router.message((F.text.lower().startswith("мой брак")) & (F.chat.type.in_(["group", "supergroup"])))
async def my_marriage_handler(msg: Message):
    """Команда: мой брак"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    user_id = int(msg.from_user.id)
    
    marriage = await get_user_marriage(chat_id, user_id)
    if not marriage:
        await msg.reply("❌ Вы не женаты.")
        return
    
    mention_1 = await mention_user_with_delay(bot=bot, chat_id=chat_id, user_id=int(marriage["participants"][0]))
    mention_2 = await mention_user_with_delay(bot=bot, chat_id=chat_id, user_id=int(marriage["participants"][1]))
    now = datetime.now(timezone.utc)
    duration = TimedeltaFormatter.format(now-marriage["date"], suffix="none")

    ans = f"👰👨‍⚖️ Брак между {mention_1} и {mention_2}:\n\n"
    ans += f"🗓 Зарегистрирован {marriage["date"]:%d.%m.%Y}\n"
    ans += f"⌛ Длится уже {duration}\n"

    await msg.reply_photo(photo=MARRIAGES_PICTURE_ID, caption=ans, parse_mode="HTML")

@router.message(
    (F.text.regexp(r"^брак(?:\s|$)", flags=re.IGNORECASE)) & 
    (F.chat.type.in_(["group", "supergroup"]))
)
async def propose(msg: Message):
    """Команда: брак {упоминание}"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    trigger_user_id = int(msg.from_user.id)
    target_user = await parse_user_mention(bot, msg)

    if msg.reply_to_message and not target_user:
        target_user = msg.reply_to_message.from_user
    
    if not target_user:
        await msg.reply("❌ Укажите пользователя, которому хотите сделать предложение.")
        return
    target_user_id = int(target_user.id)

    if target_user.is_bot:
        await msg.reply("❌ Вы не можете поженится с ботом.")
        return

    if target_user_id == trigger_user_id:
        await msg.reply("❌ Вы не можете жениться на самом себе.")
        return
    
    loyality = await check_marriage_loyality(bot, chat_id, trigger_user_id, target_user_id)
    if not loyality: return

    ic = await incest_cycle(int(msg.chat.id), trigger_user_id, target_user_id)
    if ic:
        ans = "❌ Вы не можете заключить брак со своим предком."
        await msg.reply(text=ans, parse_mode="HTML")
        return

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💍 Сказать «Да»", callback_data=f"marriage,{trigger_user_id},{target_user_id},accept"),
        InlineKeyboardButton(text="💔 Отказать", callback_data=f"marriage,{trigger_user_id},{target_user_id},decline")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Отозвать", callback_data=f"marriage,{trigger_user_id},{target_user_id},retire")
    )

    target_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    trigger_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=msg.from_user)

    ans = f"🎊 {target_user_mention}, вас приглашают к алтарю!\n"
    ans += f"💞 {trigger_user_mention} просит вашей руки и сердца.\n"
    ans += f"💫 Согласны ли вы стать парой?"

    await msg.reply_photo(
        photo=MARRIAGES_PICTURE_ID, caption=ans,
        reply_markup=builder.as_markup(), parse_mode="HTML"
    )

@router.message((F.text.lower().startswith("развод")) & (F.chat.type.in_(["group", "supergroup"])))
async def divorce(msg: Message):
    """Команда: развод"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    trigger_user_id = int(msg.from_user.id)

    success = await delete_marriage_and_notify(bot, chat_id, trigger_user_id)
    if not success:
        await msg.reply("❌ Вы не женаты.", parse_mode="HTML") 

@router.message(
    (
        (F.text.regexp(r"^усыновить(?:\s|$)", flags=re.IGNORECASE)) | 
        (F.text.regexp(r"^удочерить(?:\s|$)", flags=re.IGNORECASE))
    ) & (F.chat.type.in_(["group", "supergroup"]))
)
async def adopt(msg: Message):
    """Команда: усыновить/удочерить {упоминание}"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    trigger_user_id = int(msg.from_user.id)
    target_user = await parse_user_mention(bot, msg)

    if msg.reply_to_message and not target_user:
        target_user = msg.reply_to_message.from_user
    
    if not target_user:
        await msg.reply(f"❌ Укажите пользователя, родителем которого хотите стать.", parse_mode="HTML")
        return
    target_user_id = int(target_user.id)

    if target_user.is_bot:
        await msg.reply(f"❌ Вы не можете стать родителем бота.", parse_mode="HTML")
        return

    if target_user_id == trigger_user_id:
        await msg.reply(f"❌ Вы не можете стать своим родителем.", parse_mode="HTML")
        return
    
    marriage = await get_user_marriage(chat_id, trigger_user_id)
    if not marriage:
        await msg.reply(f"❌ Вы должны быть в браке, стать родителем.", parse_mode="HTML")
        return

    adoption_possibility = await check_adoption_possibility(chat_id, target_user_id, marriage)
    if not adoption_possibility.get("success", False):
        await msg.reply(f"❌ {adoption_possibility.get('error', 'Вы не можете стать родителем.')}", parse_mode="HTML")
        return

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💝 Вступить", callback_data=f"adoption,{trigger_user_id},{target_user_id},accept"),
        InlineKeyboardButton(text="😔 Отказать", callback_data=f"adoption,{trigger_user_id},{target_user_id},decline")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Отозвать", callback_data=f"adoption,{trigger_user_id},{target_user_id},retire")
    )

    target_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    trigger_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=msg.from_user)

    ans = f"👨‍👩‍👧 {target_user_mention}, {trigger_user_mention} хочет стать вашим родителем!\n"
    ans += f"🏡 Готовы ли вы вступить в эту семью?"

    await msg.reply(text=ans,
        reply_markup=builder.as_markup(), parse_mode="HTML"
    )

@router.message(
    (F.text.regexp(r"^бросить(?:\s|$)", flags=re.IGNORECASE)) & 
    (F.chat.type.in_(["group", "supergroup"]))
)
async def abandon_child(msg: Message):
    """Команда: сдать в детдом"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    trigger_user_id = int(msg.from_user.id)
    target_user = await parse_user_mention(bot, msg)

    if msg.reply_to_message and not target_user:
        target_user = msg.reply_to_message.from_user
    
    if not target_user:
        await msg.reply(f"❌ Укажите пользователя, которого хотите сдать в детдом.")
        return
    target_user_id = int(target_user.id)

    if target_user.is_bot:
        await msg.reply(f"❌ Вы не можете сдать в детдом бота.")
        return

    if target_user_id == trigger_user_id:
        await msg.reply(f"❌ Вы не можете сдать в детдом самого себя.")
        return
    
    parent = await is_parent(chat_id, trigger_user_id, target_user_id)
    if not parent:
        await msg.reply(f"❌ Вы не являетесь родителем этого пользователя.")
        return

    target_user_mention = await mention_user(bot=bot, chat_id=chat_id,user_entity=target_user)
    trigger_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=msg.from_user)

    ans = f"💔 {target_user_mention}, тяжёлые новости...\n"
    ans += f"😔 {trigger_user_mention} отказался от родительских прав.\n"
    ans += f"🍂 Вы больше не часть их семьи..."

    await abandon(chat_id, target_user_id)

    await msg.reply(text=ans, parse_mode="HTML")

@router.message(((F.text.lower().startswith("уйти из семьи")) | (F.text.lower().startswith("покинуть семью"))) & (F.chat.type.in_(["group", "supergroup"])))
async def abandon_parent(msg: Message):
    """Команда: уйти из семьи"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    trigger_user_id = int(msg.from_user.id)
    
    parent = await is_child(chat_id, trigger_user_id)
    if not parent:
        await msg.reply(f"❌ У вас нету семьи из которой вы могли бы уйти.")
        return

    trigger_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=msg.from_user)

    ans = f"🧑‍🧑‍🧒 {trigger_user_mention}, вы успешно покинули семью.\n"
    ans += f"💔 Надеюсь это было взвешенное решение.."

    await abandon(chat_id, trigger_user_id)

    await msg.reply(text=ans, parse_mode="HTML")

@router.message(((F.text.lower().startswith("семейное древо")) | (F.text.lower().startswith("моя семья"))) & (F.chat.type.in_(["group", "supergroup"])))
async def family_tree_handler(msg: Message):
    """Команда: семейное древо/моя семья"""
    await family_tree(msg.bot, int(msg.chat.id), int(msg.from_user.id), msg.from_user)
