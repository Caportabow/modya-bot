import asyncio
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ChatMemberUpdated, BufferedInputFile

from config import TOKEN, API_ID, API_HASH

from utils.middlewares import setup_middlewares
from db import init_db, top_users, upsert_user, user_stats, plot_user_activity, remove_user, set_nickname, add_quote, get_random_quote, get_next_messages, get_uid
from utils.stats import get_since
from utils.roleplay import parse_rp_command
from utils.quotes import make_quote
from utils import mention_user, parse_user_mention
from utils.media import get_user_avatar, get_message_media, get_file_bytes, get_mime_type

from telethon import TelegramClient

telethon_client = TelegramClient("bot", API_ID, API_HASH)

dp = setup_middlewares(Dispatcher())
bot = Bot(token=TOKEN)

# --------------------
# Helper functions
# --------------------

async def sync_members(chat_id: int):
    """Синхронизируем список участников чата."""
    async for user in telethon_client.iter_participants(chat_id):
        await upsert_user(int(chat_id), int(user.id), user.username, user.first_name)

# --------------------
# Aiogram handlers
# --------------------

# TODO: калл
# TODO: варны и награды
# TODO: просмотр всех команд с обьяснениями

@dp.message((F.text.lower().startswith("/q")) & (F.chat.type.in_(["group", "supergroup"])))
async def quotes_handler(msg: Message):
    if not msg.reply_to_message or not msg.reply_to_message.from_user: await msg.reply("❌ Ответьте на сообщение, чтобы создать цитату."); return
    
    parts = msg.text.split()
    one_quote = len(parts) == 1 or not parts[1].isdigit() or int(parts[1]) < 1
    if not one_quote and int(parts[1]) > 5:
        await msg.reply("❌ Слишком много сообщений для цитаты (макс 5).")
        return

    avatars = {}
    
    text = msg.reply_to_message.text or msg.reply_to_message.caption or ""
    media = await get_message_media(bot, msg.reply_to_message)
    if not text.strip() and not media:
        await msg.reply("❌ Это сообщение невозможно цитировать.")
        return
    
    user = msg.reply_to_message.from_user
    if msg.reply_to_message.forward_from: user = msg.reply_to_message.forward_from
    name = user.full_name
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

            # Получаем медиа, если есть
            media = None
            if media_id:
                media_bytes = await get_file_bytes(bot, media_id)
                mime_type = await get_mime_type(media_bytes)
                if mime_type:
                    media = {"source": media_bytes, "type": mime_type}

            if not text.strip() and not media: continue

            if uid in avatars:
                avatar = avatars[uid]
            else:
                avatar = await get_user_avatar(bot, uid)
                avatars[uid] = avatar

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

@dp.message((F.text.lower().startswith("кто")) & (F.chat.type.in_(["group", "supergroup"])))
async def user_info_handler(msg: Message):
    """Команда: кто [я|ты]"""
    parts = msg.text.split()
    if len(parts) <= 1: return
    target = parts[1].lower()
    
    if target == "я": user = msg.from_user

    elif target == "ты" and msg.reply_to_message: user = msg.reply_to_message.from_user

    elif target == "ты" and not msg.reply_to_message and msg.entities:
        user = await parse_user_mention(msg)
        if not user:
            await msg.reply("❌ Не удалось найти пользователя.")
            return
    
    else: return

    stats = await user_stats(int(msg.chat.id), int(user.id))
    img = await plot_user_activity(int(msg.chat.id), int(user.id))
    if not stats or not img:
        if user.is_bot:
            await msg.reply("❌ Эта команда не поддерживает ботов.")
            return
        await msg.reply("❌ Нет данных по этому пользователю.")
        return
    
    mention = await mention_user(bot=bot, chat_id=int(msg.chat.id), user_entity=user)

    ans = f"👤 Это пользователь {mention}\n\n"
    if stats["favorite_word"]:
        fav_word = stats["favorite_word"]["word"]
        fav_word_count = stats["favorite_word"]["count"]

        fav_user_id = await get_uid(int(msg.chat.id), fav_word)

        if not fav_user_id:
            ans += f"Любимое слово: {fav_word} ({fav_word_count} р.)\n"
        else:
            fav_user_mention = await mention_user(bot=bot, chat_id=int(msg.chat.id), user_id=int(fav_user_id))
            ans += f'Любимый участник: {fav_user_mention} ({fav_word_count} р.)\n'
    ans += f"Первое появление: {stats["first_seen"]}\n"
    ans += f"Последний актив: {stats["last_active"]}\n"
    ans += f"Актив за последние (24ч|7дн|30дн|∞): {stats["activity"]}\n"

    uploaded_img = BufferedInputFile(img, filename="stats.png")

    await bot.send_photo(chat_id=msg.chat.id,
                photo=uploaded_img,
                caption=ans, reply_to_message_id=msg.message_id, 
                parse_mode="HTML"
    )

@dp.message((F.text.lower().startswith("топ")) & (F.chat.type.in_(["group", "supergroup"])))
async def stats_handler(msg: Message):
    """Команда: топ [день|неделя|месяц|год|вся]"""
    parts = msg.text.split()
    period = parts[1] if len(parts) > 1 else "вся"

    try:
        since, beauty_since = get_since(period)
    except ValueError:
        return
    
    top = await top_users(int(msg.chat.id), since=since)
    ans = f"📊 Топ сообщений за {beauty_since}:\n\n"
    msg_count = 0

    for i, u in enumerate(top):
        mention = await mention_user(bot=bot, chat_id=int(msg.chat.id), user_id=int(u["user_id"]))
        
        ans += f"{i}. {mention} - {u["count"]}\n"
        msg_count += u["count"]
    ans += f"\nВсего сообщений: {msg_count}"

    await msg.reply(ans, parse_mode="HTML")

@dp.message((F.text.lower().startswith("+ник")) & (F.chat.type.in_(["group", "supergroup"])))
async def set_nick(msg: Message):
    """Команда: +ник NICKNAME"""
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply("❌ Укажите ник: +ник Вася")
        return
    nickname = parts[1].strip()
    await set_nickname(int(msg.chat.id), int(msg.from_user.id), nickname)
    await msg.reply(f"✅ Ваш ник изменён на: {nickname}")

@dp.message((F.text.lower().startswith("-ник")) & (F.chat.type.in_(["group", "supergroup"])))
async def unset_nick(msg: Message):
    """Команда: -ник (сброс ника)"""
    await set_nickname(int(msg.chat.id), int(msg.from_user.id), msg.from_user.first_name)
    await msg.reply("✅ Ваш ник сброшен.")

@dp.message()
async def on_message(msg: Message):
    if msg.chat.type in ("group", "supergroup") and msg.from_user:
        user = msg.from_user
        chat = msg.chat

        # рп команды
        if msg.text:
            target_user_entity = None

            if msg.reply_to_message and msg.reply_to_message.from_user:
                target_user_entity = msg.reply_to_message.from_user
            
            if not target_user_entity and msg.entities:
                # Пытаемся найти упоминание пользователя в тексте
                for entity in msg.entities:
                    if entity.type == "text_mention" and entity.user:
                        target_user_entity = entity.user
    
            command = await parse_rp_command(
                bot, int(chat.id), msg.text,
                user, target_user_entity
            )

            if command:
                await msg.reply(command, parse_mode="HTML")
                return
        
        # выдача рандомной цитаты
        if random.random() < 0.005:  # ~0.1% шанс
            quote_sticker_id = await get_random_quote(int(msg.chat.id))
            if quote_sticker_id:
                await bot.send_sticker(
                    chat_id=msg.chat.id,
                    sticker=quote_sticker_id,
                    reply_to_message_id=msg.message_id
                )

@dp.chat_member()
async def on_chat_member(update: ChatMemberUpdated):
    """Реагируем на добавление бота в чат или на изменения участников."""
    user = update.from_user
    uid = int(user.id)
    cid = (int(update.chat.id))

    # Если в чат добавили именно бота
    if uid == (await bot.me()).id and update.new_chat_member.status in ("administrator", "member"):
        # Бот только что добавлен в чат → синкаем участников
        asyncio.create_task(sync_members(update.chat.id))

    elif update.new_chat_member.status in ("left", "kicked"):
        await remove_user(cid, uid)
    elif update.new_chat_member.status in ("member", "administrator"):
        await upsert_user(cid, uid, user.username, user.first_name)


async def main():
    await init_db()
    await telethon_client.start(bot_token=TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
