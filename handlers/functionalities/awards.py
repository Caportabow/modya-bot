from aiogram import Router, F
from aiogram.types import Message

from utils.telegram.users import mention_user, parse_user_mention
from utils.telegram.message_templates import generate_awards_msg
from db import add_award, remove_award

router = Router(name="awards")


@router.message(((F.text.lower().startswith("наградить")) | (F.text.lower().startswith("+награда"))) & (F.chat.type.in_(["group", "supergroup"])))
async def add_award_handler(msg: Message):
    """Команда: наградить @user [причина]"""
    bot = msg.bot
    giver_id = int(msg.from_user.id)
    chat_id = int(msg.chat.id)

    target_user = None
    text_sep = msg.text.split("\n")
    award = text_sep[1] if len(text_sep) > 1 else None
    if not award:
        await msg.reply("❌ Укажите награду пользователя.")
        return
    
    if len(award) > 80:
        await msg.reply("❌ Слишком длинная награда (макс 80 символов).")
        return

    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user:
        await msg.reply("❌ Не удалось найти пользователя.")
        return
    
    if giver_id == int(target_user.id):
        await msg.reply("❌ Нельзя награждать самого себя.")
        return

    await add_award(chat_id, int(target_user.id), giver_id, award)
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    await msg.reply(f"✅ Награда \"{award}\" выдана пользователю {mention}", parse_mode="HTML")

@router.message((F.text.lower().startswith("награды")) & (F.chat.type.in_(["group", "supergroup"])))
async def get_awards_handler(msg: Message):
    """Команда: награды @user"""
    bot = msg.bot
    target_user = None

    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user: target_user = msg.from_user

    ans = await generate_awards_msg(bot, int(msg.chat.id), target_user)

    await msg.reply(ans, parse_mode="HTML")

@router.message(((F.text.lower().startswith("снять награду")) | (F.text.lower().startswith("-награда"))) & (F.chat.type.in_(["group", "supergroup"])))
async def remove_award_handler(msg: Message):
    """Команда: -награда INDEX"""
    target_id = int(msg.from_user.id)
    chat_id = int(msg.chat.id)

    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        award_index = None
    else: award_index = int(parts[1]) - 1  # пользователь вводит с 1, а в коде с 0

    success = await remove_award(chat_id, target_id, award_index)
    if success:
        await msg.reply(f"✅ Награда{f' #{award_index+1}' if award_index else ''} снята успешно.", parse_mode="HTML")
    else:
        await msg.reply("❌ Не удалось снять награду. Проверьте правильность индекса." if award_index is not None else "❌ У вас нет наград.")
