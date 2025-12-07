from aiogram import Router, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, InlineKeyboardButton, BufferedInputFile

from utils.telegram.message_templates import check_marriage_loyality, delete_marriage_and_notify
from utils.telegram.users import mention_user_with_delay, parse_user_mention, mention_user
from config import MARRIAGES_PICTURE_ID, MAX_MESSAGE_LENGTH
from db.marriages import get_marriages, get_user_marriage
from db.marriages.families import check_adoption_possibility, is_parent, is_child, abandon, get_family_tree_data, incest_cycle
from utils.web.families import make_family_tree

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
    
    ans_header = f"💍 Браки этого чата:\n\n"
    answers = []
    ans = ans_header

    for i, m in enumerate(marriages):
        mention_1 = await mention_user_with_delay(bot=bot, chat_id=chat_id, user_id=int(m["participants"][0]))
        mention_2 = await mention_user_with_delay(bot=bot, chat_id=chat_id, user_id=int(m["participants"][1]))
        
        line = f"{i+1}. {mention_1} + {mention_2} - {m["date"]}\n"

        # если добавление строки превысит лимит — отправляем текущее сообщение и начинаем новое
        if len(ans) + len(line) >= MAX_MESSAGE_LENGTH:
            answers.append(ans)
            ans = ans_header  # сбрасываем накопленное сообщение
        
        ans += line
    
    # добавляем остаток, если есть
    if ans.strip(): answers.append(ans)

    for ans in answers:   
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

    ans = f"👰👨‍⚖️ Брак между {mention_1} и {mention_2}:\n\n"
    ans += f"🗓 Зарегистрирован {marriage["date"]:%d.%m.%Y}\n"
    ans += f"⌛ Длится уже {marriage["duration"]}\n"

    await msg.reply_photo(photo=MARRIAGES_PICTURE_ID, caption=ans, parse_mode="HTML")

@router.message((F.text.lower().startswith("брак")) & (F.chat.type.in_(["group", "supergroup"])))
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
        InlineKeyboardButton(text="✅ Принять", callback_data=f"marriage,{trigger_user_id},{target_user_id},accept"),
        InlineKeyboardButton(text="❌ Отказаться", callback_data=f"marriage,{trigger_user_id},{target_user_id},decline")
    )
    builder.row(
        InlineKeyboardButton(text="🏃 Отозвать предложение", callback_data=f"marriage,{trigger_user_id},{target_user_id},retire")
    )

    target_user_mention = await mention_user(bot=bot, user_entity=target_user)
    trigger_user_mention = await mention_user(bot=bot, user_entity=msg.from_user)

    ans = f"💍 {target_user_mention}, минуточку внимания.\n"
    ans += f"💖 {trigger_user_mention} делает вам предложение руки и сердца!"

    await msg.reply_photo(
        photo=MARRIAGES_PICTURE_ID, caption=ans,
        reply_markup=builder.as_markup(), parse_mode="HTML"
    )

@router.message((F.text.lower().startswith("развод")) & (F.chat.type.in_(["group", "supergroup"])))
async def divorce(msg: Message):
    """Команда: брак {упоминание}"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    trigger_user_id = int(msg.from_user.id)

    success = await delete_marriage_and_notify(bot, chat_id, trigger_user_id)
    if not success:
        await msg.reply("❌ Вы не женаты.", parse_mode="HTML") 

@router.message(((F.text.lower().startswith("усыновить")) | (F.text.lower().startswith("удочерить"))) & (F.chat.type.in_(["group", "supergroup"])))
async def adopt(msg: Message):
    """Команда: усыновить/удочерить {упоминание}"""
    action = msg.text.split()[0].lower()
    bot = msg.bot
    chat_id = int(msg.chat.id)
    trigger_user_id = int(msg.from_user.id)
    target_user = await parse_user_mention(bot, msg)

    if msg.reply_to_message and not target_user:
        target_user = msg.reply_to_message.from_user
    
    if not target_user:
        await msg.reply(f"❌ Укажите пользователя, которого хотите {action}.", parse_mode="HTML")
        return
    target_user_id = int(target_user.id)

    if target_user.is_bot:
        await msg.reply(f"❌ Вы не можете {action} бота.", parse_mode="HTML")
        return

    if target_user_id == trigger_user_id:
        await msg.reply(f"❌ Вы не можете {action} самого себя.", parse_mode="HTML")
        return
    
    marriage = await get_user_marriage(chat_id, trigger_user_id)
    if not marriage:
        await msg.reply(f"❌ Вы должны быть в браке, чтобы {action} кого-нибудь.", parse_mode="HTML")
        return

    adoption_possibility = await check_adoption_possibility(chat_id, target_user_id, marriage)
    if not adoption_possibility.get("success", False):
        await msg.reply(f"❌ {adoption_possibility.get('error', 'Вы не можете стать родителем.')}", parse_mode="HTML")
        return

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Принять", callback_data=f"adoption,{trigger_user_id},{target_user_id},accept"),
        InlineKeyboardButton(text="❌ Отказаться", callback_data=f"adoption,{trigger_user_id},{target_user_id},decline")
    )
    builder.row(
        InlineKeyboardButton(text="🏃 Отозвать предложение", callback_data=f"adoption,{trigger_user_id},{target_user_id},retire")
    )

    target_user_mention = await mention_user(bot=bot, user_entity=target_user)
    trigger_user_mention = await mention_user(bot=bot, user_entity=msg.from_user)

    ans = f"❗️{target_user_mention}, внимание.\n"
    ans += f"🍼 {trigger_user_mention} хочет принять вас в свою семью!"

    await msg.reply(text=ans,
        reply_markup=builder.as_markup(), parse_mode="HTML"
    )

@router.message(((F.text.lower().startswith("сдать в детдом")) | (F.text.lower().startswith("отказаться от ребёнка"))) & (F.chat.type.in_(["group", "supergroup"])))
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

    target_user_mention = await mention_user(bot=bot, user_entity=target_user)
    trigger_user_mention = await mention_user(bot=bot, user_entity=msg.from_user)

    ans = f"💔 {target_user_mention}, мне очень жаль..\n"
    ans += f"🏠 {trigger_user_mention} сдает вас в детдом, вы больше не являетесь его ребёнком"

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

    trigger_user_mention = await mention_user(bot=bot, user_entity=msg.from_user)

    ans = f"🧑‍🧑‍🧒 {trigger_user_mention}, вы успешно покинули семью.\n"
    ans += f"💔 Надеюсь это было взвешенное решение.."

    await abandon(chat_id, trigger_user_id)

    await msg.reply(text=ans, parse_mode="HTML")

@router.message(((F.text.lower().startswith("семейное древо")) | (F.text.lower().startswith("моя семья"))) & (F.chat.type.in_(["group", "supergroup"])))
async def family_tree_handler(msg: Message):
    """Команда: семейное древо/моя семья"""
    bot = msg.bot
    chat_id = int(msg.chat.id)
    user_id = int(msg.from_user.id)
    
    family_tree_data = await get_family_tree_data(chat_id, user_id)
    if not family_tree_data or len(family_tree_data) == 0:
        await msg.reply("❌ Вы не состоите в какой-либо семье.")
        return
    
    family_tree_bytes = await make_family_tree(family_tree_data)
    family_tree = BufferedInputFile(family_tree_bytes, filename="family_tree.jpeg")
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=msg.from_user)

    await msg.reply_photo(photo=family_tree, caption=f"🌳 Семейное древо {mention}:", parse_mode="HTML")
