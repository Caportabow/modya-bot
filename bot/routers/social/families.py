import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from services.messages.family import generate_family_tree_msg
from services.telegram.user_mention import mention_user
from services.telegram.user_parser import parse_user_mention

from services.telegram.keyboards.families import AdoptionRequest, get_adoption_request_keyboard
from db.marriages import get_user_marriage
from db.marriages.families import adopt_child, check_adoption_possibility, is_parent, is_child, abandon

router = Router(name="marriages")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


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

    keyboard = await get_adoption_request_keyboard(trigger_user_id, target_user_id)

    target_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    trigger_user_mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=msg.from_user)

    ans = f"👨‍👩‍👧 {target_user_mention}, {trigger_user_mention} хочет стать вашим родителем!\n"
    ans += f"🏡 Готовы ли вы вступить в эту семью?"

    await msg.reply(text=ans,
        reply_markup=keyboard, parse_mode="HTML"
    )

@router.message(
    F.text.regexp(r"^бросить(?:\s|$)", flags=re.IGNORECASE)
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

@router.message(
    F.text.lower().startswith("уйти из семьи") |
    F.text.lower().startswith("покинуть семью")
)
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

# TODO: сделать команду cемья @user — показать семейное древо указанного пользователя
@router.message(
    F.text.lower().startswith("семейное древо") |
    F.text.lower().startswith("моя семья")
)
async def family_tree_handler(msg: Message):
    """Команда: семейное древо/моя семья"""
    text, keyboard, img = await generate_family_tree_msg(msg.bot, int(msg.chat.id), msg.from_user)
    if not text:
        await msg.reply("❌ Вы пока не состоите в семье.", parse_mode="HTML")
        return

    await msg.reply_photo(
        photo=img,
        caption=text, reply_to_message_id=msg.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(AdoptionRequest.filter(F.response == "accept"))
async def adoption_accept_callback_handler(callback: CallbackQuery, callback_data: AdoptionRequest):
    """Обрабатывает согласие на предложение усыновления/удочерения."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return

    chat_id = int(msg.chat.id)

    # Проверка прав доступа
    if int(callback.from_user.id) != callback_data.target_user_id:
        await callback.answer(text="❌ Вы не можете ответить на чужое предложение.", show_alert=True)
        return

    await msg.edit_reply_markup()
    target_user = await mention_user(bot=bot, chat_id=chat_id, user_id=callback_data.target_user_id)
    trigger_user = await mention_user(bot=bot, chat_id=chat_id, user_id=callback_data.trigger_user_id)

    adoption_possibility = await check_adoption_possibility(chat_id, callback_data.target_user_id, parent_id=callback_data.trigger_user_id)
    if not adoption_possibility.get("success", False):
        await callback.answer(text="❌ Вы не можете выдать рест самому себе.", show_alert=True)
        await msg.edit_text(f"❌ {trigger_user}, {adoption_possibility.get('error', 'Вы не можете быть усыновлены.')}", parse_mode="HTML")
        return

    await adopt_child(chat_id, callback_data.trigger_user_id, callback_data.target_user_id)
    
    ans = f"👨‍👩‍👧 Поздравляем с пополнением в семье!\n💞 {trigger_user} теперь приёмный родитель {target_user}!"
    
    await msg.edit_text(text=ans, parse_mode="HTML")

@router.callback_query(AdoptionRequest.filter(F.response == "decline"))
async def adoption_decline_callback_handler(callback: CallbackQuery, callback_data: AdoptionRequest):
    """Обрабатывает отказ от предложения усыновления/удочерения."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return

    chat_id = int(msg.chat.id)

     # Проверка прав доступа
    if int(callback.from_user.id) != callback_data.target_user_id:
        await callback.answer(text="❌ Вы не можете ответить на чужое предложение.", show_alert=True)
        return

    await msg.edit_reply_markup()
    target_user = await mention_user(bot=bot, chat_id=chat_id, user_id=callback_data.target_user_id)
    trigger_user = await mention_user(bot=bot, chat_id=chat_id, user_id=callback_data.trigger_user_id)

    ans = f"💔 {trigger_user}, мне очень жаль..\n🥀 {target_user} отказался(-ась) от вашего предложения."

    await msg.edit_text(text=ans, parse_mode="HTML")

@router.callback_query(AdoptionRequest.filter(F.response == "retire"))
async def adoption_retire_callback_handler(callback: CallbackQuery, callback_data: AdoptionRequest):
    """Обрабатывает предложение усыновления/удочерения."""
    bot = callback.bot
    msg = callback.message
    if not msg or not msg.chat: return

    chat_id = int(msg.chat.id)

     # Проверка прав доступа
    if int(callback.from_user.id) != callback_data.target_user_id:
        await callback.answer(text="❌ Вы не можете ответить на чужое предложение.", show_alert=True)
        return

    await msg.edit_reply_markup()
    target_user = await mention_user(bot=bot, chat_id=chat_id, user_id=callback_data.target_user_id)
    trigger_user = await mention_user(bot=bot, chat_id=chat_id, user_id=callback_data.trigger_user_id)

    ans = f"💔 {target_user}, мне очень жаль..\n🥀 {trigger_user} передумал принимать вас в семью."

    await msg.edit_text(text=ans, parse_mode="HTML")
