from aiogram import Router, Bot
from aiogram.types import CallbackQuery, Message

from config import WARNINGS_PICTURE_ID, AWARDS_PICTURE_ID
from db.marriages import make_marriage
from db.marriages.families import adopt_child, check_adoption_possibility, incest_cycle
from utils.telegram.users import is_admin, is_creator, get_chat_member_or_fall, mention_user
from utils.telegram.message_templates import generate_awards_msg, generate_warnings_msg, generate_rest_msg, check_marriage_loyality, family_tree

router = Router(name="callback")

@router.callback_query()
async def callback_handler(callback: CallbackQuery):
    """Обработчик колбэков."""
    bot = callback.bot
    msg = callback.message
    
    if not msg:
        await callback.answer()
        return

    chat_id = int(msg.chat.id)
    parts = callback.data.split(",")
    action = parts[0]

    # Обработка брака
    if action == "marriage":
        await handle_marriage(callback, bot, msg, chat_id, parts)
    
    # Обработка усыновления/удочерения
    elif action == "adoption":
        await handle_adoption(callback, bot, msg, chat_id, parts)
    
    # Обработка реста
    elif action == "rest":
        await handle_rest(callback, bot, msg, chat_id, parts)
    
    # Обработка наград/предупреждений/семьи
    elif action in ["awards", "warnings", "family"]:
        await handle_user_info(bot, msg, chat_id, parts, action)

    await callback.answer()


async def handle_adoption(callback: CallbackQuery, bot: Bot, msg: Message, chat_id: int, parts: list):
    """Обрабатывает предложение усыновления/удочерения."""
    if len(parts) < 4:
        return

    trigger_user_id = int(parts[1])
    target_user_id = int(parts[2])
    action = parts[3]

    # Проверка прав доступа
    if action == "retire" and int(callback.from_user.id) != trigger_user_id:
        await callback.answer(text="❌ Вы не можете нажать на эту кнопку.", show_alert=True)
        return
    elif action != "retire" and int(callback.from_user.id) != target_user_id:
        await callback.answer(text="❌ Вы не можете ответить на чужое предложение.", show_alert=True)
        return

    await msg.edit_reply_markup()
    target_user = await mention_user(bot=bot, chat_id=chat_id, user_id=target_user_id)
    trigger_user = await mention_user(bot=bot, chat_id=chat_id, user_id=trigger_user_id)

    if action == "accept":
        adoption_possibility = await check_adoption_possibility(chat_id, target_user_id, parent_id=trigger_user_id)
        if not adoption_possibility.get("success", False):
            await msg.reply(f"❌ {trigger_user}, {adoption_possibility.get('error', 'Вы не можете быть усыновлены.')}", parse_mode="HTML")
            return

        await adopt_child(chat_id, trigger_user_id, target_user_id)
        
        ans = f"👨‍👩‍👧 Поздравляем с пополнением в семье!\n💞 {trigger_user} теперь приёмный родитель {target_user}!"

    elif action == "decline":
        ans = f"💔 {trigger_user}, мне очень жаль..\n🥀 {target_user} отказался(-ась) от вашего предложения."
        
    elif action == "retire":
        ans = f"💔 {target_user}, мне очень жаль..\n🥀 {trigger_user} передумал принимать вас в семью."

    
    await msg.edit_text(text=ans, parse_mode="HTML")


async def handle_marriage(callback: CallbackQuery, bot: Bot, msg: Message, chat_id: int, parts: list):
    """Обрабатывает предложение брака."""
    if len(parts) < 4:
        return

    trigger_user_id = int(parts[1])
    target_user_id = int(parts[2])
    action = parts[3]

    # Проверка прав доступа
    if action == "retire" and int(callback.from_user.id) != trigger_user_id:
        await callback.answer(text="❌ Вы не можете нажать на эту кнопку.", show_alert=True)
        return
    elif action != "retire" and int(callback.from_user.id) != target_user_id:
        await callback.answer(text="❌ Вы не можете ответить на чужое предложение.", show_alert=True)
        return

    await msg.edit_reply_markup()
    trigger_user = await mention_user(bot=bot, chat_id=chat_id, user_id=trigger_user_id)
    target_user = await mention_user(bot=bot, chat_id=chat_id, user_id=target_user_id)

    if action == "accept":
        loyality = await check_marriage_loyality(bot, chat_id, trigger_user_id, target_user_id)
        if not loyality:
            return
        
        ic = await incest_cycle(int(msg.chat.id), trigger_user_id, target_user_id)
        if ic:
            ans = "❌ Вы не можете заключить брак со своим предком."
            await msg.reply(text=ans, parse_mode="HTML")
            return

        result = await make_marriage(chat_id, [trigger_user_id, target_user_id])
        failure = not result.get("success", False) if isinstance(result, dict) else False

        if failure:
            ans = "❌ Брак не может быть заключён, кто-то из участников уже в браке."
            await msg.reply(text=ans, parse_mode="HTML")
            return
        
        ans = f"💍 Поздравляем молодоженов!\n💝 С сегодняшнего дня {trigger_user} и {target_user} женаты!"
        
    elif action == "decline":
        ans = f"💔 {trigger_user}, мне очень жаль..\n🥀 {target_user} отказался(-ась) от вашего предложения."
            
    elif action == "retire":
        ans = f"💔 {target_user}, мне очень жаль..\n💍 {trigger_user} аннулировал предложение о заключении брака."
    
    await msg.edit_caption(caption=ans, parse_mode="HTML")


async def handle_rest(callback: CallbackQuery, bot: Bot, msg: Message, chat_id: int, parts: list):
    """Обрабатывает выдачу реста."""
    data = parts[1]
    trigger_user = callback.from_user
    target_user = msg.reply_to_message.from_user
    trigger_user_id = int(trigger_user.id)

    if data == "retire":
        if trigger_user_id != int(target_user.id):
            await callback.answer(text="❌ Вы не можете нажать на эту кнопку.", show_alert=True)
            return
        
        await msg.delete()
        return

    # Проверка на самого себя
    if trigger_user_id == int(target_user.id):
        creator = await is_creator(bot, chat_id, trigger_user_id)
        if not creator:
            await msg.reply("❌ Вы не можете выдать рест самому себе.", parse_mode="HTML")
            return

    # Проверка прав администратора
    admin = await is_admin(bot, chat_id, trigger_user_id)
    if not admin:
        await msg.reply(text="❌ Вы должны быть админом, чтобы выдать рест.", parse_mode="HTML")
        return

    ans = await generate_rest_msg(bot, chat_id, data, trigger_user, target_user)
    
    await msg.edit_reply_markup()
    await msg.edit_text(text=ans, parse_mode="HTML")

async def handle_user_info(bot: Bot, msg: Message, chat_id: int, parts: list, action: str):
    """Обрабатывает запросы наград и предупреждений."""
    if len(parts) < 2 or not parts[1].isdigit():
        return

    user_id = int(parts[1])
    member = await get_chat_member_or_fall(bot=bot, chat_id=chat_id, user_id=user_id)
    if not member:
        return

    user = member.user
    user_id = int(user.id)
    
    if action == "family":
        await family_tree(bot, chat_id, user_id, user)
        return
    
    elif action == "awards":
        answers = await generate_awards_msg(bot, chat_id, user)
        photo = AWARDS_PICTURE_ID
    else: # action == "warnings"
        answers = await generate_warnings_msg(bot, chat_id, user)
        photo = WARNINGS_PICTURE_ID

    for ans in answers:
        await msg.reply_photo(
            photo=photo, 
            caption=ans, 
            reply_to_message_id=msg.message_id, 
            parse_mode="HTML"
        )
