from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile

from utils.telegram.media import get_message_media, get_user_avatar, get_file_bytes, get_mime_type
from utils.quotes import make_quote
from db import add_quote, get_next_messages

router = Router(name="quotes")


@router.message((F.text.lower().startswith("/q")) & (F.chat.type.in_(["group", "supergroup"])))
async def quotes_handler(msg: Message):
    """Команда: /q [кол-во сообщений]"""
    bot = msg.bot

    reply = msg.reply_to_message
    if not reply or not reply.from_user:
        await msg.reply("❌ Ответьте на сообщение, чтобы создать цитату.")
        return
    
    parts = msg.text.split()
    one_quote = len(parts) == 1 or not parts[1].isdigit() or int(parts[1]) < 1
    if not one_quote and int(parts[1]) > 5:
        await msg.reply("❌ Слишком много сообщений для цитаты (макс 5).")
        return

    avatars = {}
    avatar = None
    
    text = reply.text or reply.caption or ""
    media = await get_message_media(bot, reply)
    if not text.strip() and not media:
        await msg.reply("❌ Это сообщение невозможно цитировать.")
        return

    user = reply.from_user if not reply.forward_from else reply.forward_from
    name = reply.forward_sender_name or user.full_name

    is_forward = bool(reply.forward_from or reply.forward_sender_name)
    if not is_forward:
        avatar = await get_user_avatar(bot, int(user.id))
        avatars[int(user.id)] = avatar

    quote_materials = [{"name": name, "text": text, "avatar": avatar, "media": media}]

    if not one_quote:
        msg_quantity = int(parts[1]) + 1 # включаем родительское сообщение, которое в счёт не идёт
        first_msg_id = msg.reply_to_message.message_id
        msgs = await get_next_messages(int(msg.chat.id), int(first_msg_id), msg_quantity - 1)
        for m in msgs:
            name = m["name"]
            text = m["text"]
            uid = int(m["user_id"])
            media_id = m["file_id"]
            is_forward = m["is_forward"]

            # Получаем медиа, если есть
            media = None
            if media_id:
                media_bytes = await get_file_bytes(bot, media_id)
                mime_type = await get_mime_type(media_bytes)
                if mime_type:
                    media = {"source": media_bytes, "type": mime_type}

            if not text.strip() and not media: continue
            
            if not is_forward:
                if uid in avatars:
                    avatar = avatars[uid]
                else:
                    avatar = await get_user_avatar(bot, uid)
                    avatars[uid] = avatar
            else:
                avatar = None

            quote_materials.append({"name": name, "text": text, "avatar": avatar, "media": media})
            if len(quote_materials) >= msg_quantity: break

    quote = await make_quote(quote_materials)
    quote_file = BufferedInputFile(quote, filename="quote.webp")
    
    sent_msg = await bot.send_sticker(
        chat_id=msg.chat.id, sticker=quote_file,
        reply_to_message_id=msg.message_id
        )
    
    if sent_msg.sticker:
        sticker_id = sent_msg.sticker.file_id
        await add_quote(int(msg.chat.id), str(sticker_id))
