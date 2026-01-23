import random
from aiogram import Router, F
from aiogram.types import Message

from db.users.rp_commands import get_user_rp_commands
from db.quotes import get_random_quote

from middlewares.maintenance import MaintenanceMiddleware
from services.telegram.keyboards.quotes import get_quote_delition_keyboard
from services.process_roleplay import parse_rp_command
from services.telegram.user_parser import parse_user_mention_and_clean_text

router = Router(name="groups")
router.message.middleware(MaintenanceMiddleware(notify=False))
router.callback_query.middleware(MaintenanceMiddleware(notify=False))


@router.message(F.chat.type.in_(["group", "supergroup"]))
async def on_message(msg: Message):
    # Пробуем обработать как RP команду
    bot = msg.bot
    user = msg.from_user
    chat = msg.chat
    text = msg.text or msg.caption

    if text and user and bot:
        # Удаляем префиксы
        prefixes = ["!", "/", "-", "—", "."]
        text = text.lstrip("".join(prefixes))

        # Упоминание пользователя в тексте
        target_user_entity, text = await parse_user_mention_and_clean_text(bot, msg)
        if not text: return # Если текст пустой после удаления упоминания, то сразу пропускаем

        if not target_user_entity:
            if msg.reply_to_message and msg.reply_to_message.from_user:
                # Реплай на пользователя
                target_user_entity = msg.reply_to_message.from_user
            # Если target_user_entity стал None, то действие направлено на самих нас

        user_rp_commands = await get_user_rp_commands(int(chat.id), int(user.id))
        command = await parse_rp_command(
            bot, int(chat.id), text,
            user, target_user_entity, user_rp_commands
        )

        if command:
            await (msg.reply_to_message or msg).reply(command, parse_mode="HTML")
            return # если это ролевое сообщение, не продолжаем дальше
    
    # выдача рандомной цитаты
    if random.random() < 0.005:  # ~0.5% шанс
        quote_sticker_id = await get_random_quote(int(msg.chat.id))

        if quote_sticker_id:
            keyboard = await get_quote_delition_keyboard()

            await msg.reply_sticker(sticker=quote_sticker_id, reply_markup=keyboard)
