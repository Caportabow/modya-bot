import asyncio
import re
import time
from datetime import datetime
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ChatMemberUpdated, BufferedInputFile, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import TOKEN, API_ID, API_HASH

from utils.middlewares import setup_middlewares
from db import init_db, top_users, upsert_user, user_stats, plot_user_activity, remove_user, set_nickname, add_quote, get_random_quote, get_next_messages, get_uid, get_all_users_in_chat, add_warning, get_warnings, remove_warning, add_award, get_awards, remove_award, minmsg_users
from utils import mention_user, parse_user_mention, is_admin
from utils.stats import get_since, format_timedelta
from utils.roleplay import parse_rp_command
from utils.quotes import make_quote
from utils.media import get_user_avatar, get_message_media, get_file_bytes, get_mime_type

from telethon import TelegramClient

telethon_client = TelegramClient("bot", API_ID, API_HASH)

dp = setup_middlewares(Dispatcher())
bot = Bot(token=TOKEN)
last_call_time = {}  # Для ограничения частоты вызовов команды /call

# --------------------
# Helper functions
# --------------------

async def sync_members(chat_id: int):
    """Синхронизируем список участников чата."""
    async for user in telethon_client.iter_participants(chat_id):
        await upsert_user(int(chat_id), int(user.id), user.username, user.first_name)

async def send_welcome_message(chat_id: int, private_msg: bool = False):
    """Отправляем приветственное сообщение в чат."""
    pic_id = "AgACAgIAAyEGAAS7wxNHAANAaPrGTWcs7T0JzbfL8UzY_aqOyg0AAgbxMRuZh9lL7mXuJTHRdj8BAAMCAAN3AAM2BA"
    pre_text = "Привет! Спасибо, что добавили меня!\n\n"

    text = (pre_text if not private_msg else "") + '⚙️ С полным списком моих команд можно ознакомится в <a href="https://teletype.in/@caportabow/ModyaTheBot">этом списке</a>.'
    await bot.send_photo(photo=pic_id, caption=text, chat_id=chat_id, parse_mode="HTML")

async def generate_awards_msg(chat_id: int, target_user):
    awards = await get_awards(chat_id, int(target_user.id))
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)

    if not awards:
        return f"❕У пользователя {mention} нет наград."

    ans = f"🏆 Награды пользователя {mention}:\n\n"
    for i, w in enumerate(awards):
        award = w["award"]
        date = format_timedelta(datetime.now() - datetime.fromtimestamp(w["assigment_date"])) + " назад"
        ans += f"🎗{i+1}. {award} | {date}\n\n"
    
    return ans

async def generate_warnings_msg(chat_id: int, target_user):
    warnings = await get_warnings(chat_id, int(target_user.id))
    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)

    if not warnings:
        return f"❕У пользователя {mention} нет варнов."

    ans = f"⚠ Варны пользователя {mention}:\n\n"
    for i, w in enumerate(warnings):
        reason = w["reason"] or "Причина не указана"
        date = format_timedelta(datetime.now() - datetime.fromtimestamp(w["assigment_date"])) + " назад"
        moderator_mention = await mention_user(bot=bot, chat_id=chat_id, user_id=w["administrator_user_id"])
        ans += f"🔸{i+1}. {reason} | {date}\n      Модератор: {moderator_mention}\n\n"
    
    return ans

# --------------------
# Aiogram handlers
# --------------------

# TODO: системные сообщения
# TODO: больше картинок в описание команд
# TODO: система роутеров
# TODO: реворк ДБ где мы чекаем чтобы файлы не повторялись
# (таблица files где у каждого id, и проверяем чтобы id телеги не повторялся), 
# возможно перенос на mySQL

@dp.message(F.text.lower().startswith("/help"))
async def help_handler(msg: Message):
    """Команда: /help"""
    if msg.chat.type in ("group", "supergroup"):
        await send_welcome_message(chat_id=msg.chat.id)
    else:
        await send_welcome_message(chat_id=msg.chat.id, private_msg=True)

@dp.message((F.text.lower().startswith("/q")) & (F.chat.type.in_(["group", "supergroup"])))
async def quotes_handler(msg: Message):
    """Команда: /q [кол-во сообщений]"""
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
    
    text = reply.text or reply.caption or ""
    media = await get_message_media(bot, reply)
    if not text.strip() and not media:
        await msg.reply("❌ Это сообщение невозможно цитировать.")
        return
    
    user = reply.from_user if not reply.forward_from else reply.forward_from
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

@dp.message(((F.text.lower().startswith("/call")) | (F.text.lower().startswith("созвать"))) & (F.chat.type.in_(["group", "supergroup"])))
async def сall_members(msg: Message):
    """Команда: созвать | /call"""
    global last_call_time
    chat_id = int(msg.chat.id)
    now = time.time()
    
    if chat_id in last_call_time and now - last_call_time[chat_id] < 60:
        await msg.reply("❌ Команду можно использовать только раз в 60 секунд.")
        return
    
    arg = re.sub(r'^(\/call|созвать)\s*', '', msg.text, flags=re.IGNORECASE)
    if len(arg) > 300:
        await msg.reply("❌ Слишком длинный текст для созыва (макс 300 символов).")
        return

    admin = await is_admin(bot, chat_id, int(msg.from_user.id))
    if not admin:
        await msg.reply("❌ Только администраторы могут использовать эту команду.")
        return
    
    last_call_time[chat_id] = now # обновляем время последнего вызова

    users = await get_all_users_in_chat(chat_id)
    if not users:
        await msg.reply("❌ Нет участников для созыва.")
        return
    
    reply_msg_id = msg.reply_to_message.message_id if msg.reply_to_message else None
    
    for i in range(0, len(users), 5):
        chunk = users[i:i+5]
        text = f"⚡ {arg if arg.strip() else 'Внимание!'}\n\n"

        mentions = await asyncio.gather(*(mention_user(bot=bot, chat_id=chat_id, user_id=u) for u in chunk))
        text += "\n".join(mentions)

        if reply_msg_id:
            await bot.send_message(chat_id=chat_id, text=text, reply_to_message_id=reply_msg_id, parse_mode="HTML")
        else:
            await msg.reply(text, parse_mode="HTML")

@dp.message((F.text.lower().startswith("норма")) & (F.chat.type.in_(["group", "supergroup"])))
async def minmsg_handler(msg: Message):
    """Команда: норма {кол-во сообщений}"""
    parts = msg.text.split()
    if len(parts) > 1:
        msg_count = parts[1]
        if not msg_count.isdigit() or int(msg_count) <= 0:
            await msg.reply("❌ Укажите корректное число сообщений.")
            return
    else:
        await msg.reply("❌ Укажите минимальное количество сообщений (норму).")
        return
    
    users = await minmsg_users(int(msg.chat.id), int(msg_count))
    if not users or len(users) == 0:
        await msg.reply(f"✅ Все участники успешно набрали норму!")
        return
    ans = f"❗️Следующие участники не набрали норму в {msg_count} сообщений:\n\n"
    for i, u in enumerate(users):
        mention = await mention_user(bot=bot, chat_id=int(msg.chat.id), user_id=int(u["user_id"]))
        ans += f"{i+1}. {mention} - {u["count"]} сообщений\n"

    await msg.reply(ans, parse_mode="HTML")

@dp.message((F.text.lower().startswith("варны")) & (F.chat.type.in_(["group", "supergroup"])))
async def get_warnings_handler(msg: Message):
    """Команда: варны @user"""
    target_user = None

    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user: target_user = msg.from_user

    ans = await generate_warnings_msg(int(msg.chat.id), target_user)

    await msg.reply(ans, parse_mode="HTML")

@dp.message(((F.text.lower().startswith("+варн")) | (F.text.lower().startswith("варн"))) & (F.chat.type.in_(["group", "supergroup"])))
async def add_warning_handler(msg: Message):
    """Команда: +варн @user [причина]"""
    admin_id = int(msg.from_user.id)
    chat_id = int(msg.chat.id)

    target_user = None
    text_sep = msg.text.split("\n")
    reason = text_sep[1] if len(text_sep) > 1 else None

    if len(reason or "") > 70:
        await msg.reply("❌ Слишком длинная причина варна (макс 70 символов).")
        return

    is_admin_user = await is_admin(bot, chat_id, admin_id)
    if not is_admin_user:
        await msg.reply("❌ Только администраторы могут выдавать варны.")
        return

    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user:
        await msg.reply("❌ Не удалось найти пользователя.")
        return

    warn_id = await add_warning(chat_id, int(target_user.id), admin_id, reason)
    warn_info = f" (#{warn_id})" if warn_id else ""

    mention = await mention_user(bot=bot, chat_id=chat_id, user_entity=target_user)
    await msg.reply(f"✅ Варн{warn_info} выдан пользователю {mention}.\nПричина: {reason or 'не указана'}", parse_mode="HTML")

    if warn_id and warn_id >= 3:
        await msg.reply(f"⚠ Пользователь {mention} получил 3 и более варнов. Рекомендуется рассмотреть возможность бана.", parse_mode="HTML")

@dp.message((F.text.lower().startswith("-варн")) & (F.chat.type.in_(["group", "supergroup"])))
async def remove_warning_handler(msg: Message):
    """Команда: -варн @user INDEX"""
    admin_id = int(msg.from_user.id)
    chat_id = int(msg.chat.id)

    is_admin_user = await is_admin(bot, chat_id, admin_id)
    if not is_admin_user:
        await msg.reply("❌ Только администраторы могут снимать варны.")
        return

    parts = msg.text.split()
    if len(parts) >= 1:
        warn_index = None
    elif parts[2].isdigit():
        warn_index = int(parts[2]) - 1  # пользователь вводит с 1, а в коде с 0
    elif parts[1].isdigit():
        warn_index = int(parts[1]) - 1  # пользователь вводит с 1, а в коде с 0
    else:
        warn_index = None

    target_user = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user:
        await msg.reply("❌ Не удалось найти пользователя.")
        return

    success = await remove_warning(chat_id, int(target_user.id), warn_index)
    if success:
        await msg.reply(f"✅ Варн{f' #{warn_index+1}' if warn_index else ''} снят успешно.", parse_mode="HTML")
    else:
        await msg.reply("❌ Не удалось снять варн. Проверьте правильность индекса." if warn_index is not None else "❌ У пользователя нет варнов.")

@dp.message(((F.text.lower().startswith("наградить")) | (F.text.lower().startswith("+награда"))) & (F.chat.type.in_(["group", "supergroup"])))
async def add_award_handler(msg: Message):
    """Команда: наградить @user [причина]"""
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

@dp.message((F.text.lower().startswith("награды")) & (F.chat.type.in_(["group", "supergroup"])))
async def get_awards_handler(msg: Message):
    """Команда: награды @user"""
    target_user = None

    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    else:
        target_user = await parse_user_mention(bot, msg)

    if not target_user: target_user = msg.from_user

    ans = await generate_awards_msg(int(msg.chat.id), target_user)

    await msg.reply(ans, parse_mode="HTML")

@dp.message(((F.text.lower().startswith("снять награду")) | (F.text.lower().startswith("-награда"))) & (F.chat.type.in_(["group", "supergroup"])))
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

@dp.message((F.text.lower().startswith("кто")) & (F.chat.type.in_(["group", "supergroup"])))
async def user_info_handler(msg: Message):
    """Команда: кто [я|ты]"""
    parts = msg.text.split()
    if len(parts) <= 1: return
    target = parts[1].lower()
    
    if target == "я": user = msg.from_user

    elif target == "ты" and msg.reply_to_message: user = msg.reply_to_message.from_user

    elif target == "ты" and not msg.reply_to_message and msg.entities:
        user = await parse_user_mention(bot, msg)
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

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏆 Награды", callback_data=f"awards,{int(user.id)}"),
        InlineKeyboardButton(text="⚠ Варны", callback_data=f"warnings,{int(user.id)}")
    )

    await bot.send_photo(chat_id=msg.chat.id,
                photo=uploaded_img,
                caption=ans, reply_to_message_id=msg.message_id,
                reply_markup=builder.as_markup(),
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
        
        ans += f"{i+1}. {mention} - {u["count"]}\n"
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

    if len(nickname) > 50:
        await msg.reply("❌ Слишком длинный ник (макс 50 символов).")
        return

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
                reply_message = msg.reply_to_message if msg.reply_to_message else msg
                await reply_message.reply(command, parse_mode="HTML")
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
        # Приветственное сообщение
        await send_welcome_message(update.chat.id)

        # Бот только что добавлен в чат → синкаем участников
        asyncio.create_task(sync_members(update.chat.id))

    elif update.new_chat_member.status in ("left", "kicked"):
        await remove_user(cid, uid)
    elif update.new_chat_member.status in ("member", "administrator"):
        await upsert_user(cid, uid, user.username, user.first_name)

@dp.callback_query()
async def callback_handler(callback: CallbackQuery):
    ans = None

    if callback.message:
        parts = callback.data.split(",")
        action = parts[0]

        user_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        user = (await bot.get_chat_member(int(callback.message.chat.id), user_id)).user if user_id else None

        if user and action == "awards":
            ans = await generate_awards_msg(int(callback.message.chat.id), user)
        elif user and action == "warnings" and callback.message:
            ans = await generate_warnings_msg(int(callback.message.chat.id), user)

        if ans: await callback.message.answer(ans, reply_to_message_id=callback.message.message_id, parse_mode="HTML")

    await callback.answer()  # чтобы убрать "loading" кружок

async def main():
    await init_db()
    await telethon_client.start(bot_token=TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
