import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramNotFound, TelegramForbiddenError, TelegramNetworkError

from db import init_db, close_db
from db.chats import get_all_chat_ids, forget_chat
from config import TELEGRAM_TOKEN, MAINTENANCE_PICTURE_ID, UPDATE_PICTURE_ID

bot = Bot(token=TELEGRAM_TOKEN)


# Отправка фото по file_id
async def _send(chat_id: int, file_id: str, caption: str | None = None):
    try:
        await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption, parse_mode="HTML")

    except TelegramNotFound or TelegramForbiddenError as e:
        # Бот заблокирован, удален из группы, или
        # сама группа удалена
        await forget_chat(int(chat_id))
        return

    except TelegramNetworkError as e:
        # Проблемы с сетью/таймаут
        await asyncio.sleep(0.6)
        await _send(chat_id, file_id, caption)

    except Exception as e:
        # Неверный file_id, неподдерживаемый формат,
        # слишком большой размер файла и прочие непредвиденные ошибки
        print(f"⚠️ Unexpected error: {e}")


# Массовая отправка с ограничением числа одновременных задач
async def _preparer(file_id: str, caption: str | None = None, limit: int = 5):
    chats = await get_all_chat_ids()
    semaphore = asyncio.Semaphore(limit)  # ограничиваем параллельные запросы

    async def sem_send(chat_id):
        async with semaphore:
            await _send(chat_id, file_id, caption)

    tasks = [sem_send(chat_id) for chat_id in chats]
    await asyncio.gather(*tasks)


async def sender(active: bool, text: str = "⚙️ Ваше сообщение.\n\n"):
    picture = UPDATE_PICTURE_ID if active else MAINTENANCE_PICTURE_ID
    # Передаем file_id вместо пути к файлу
    try:
        await init_db()
        await _preparer(picture, caption=text)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(sender(False))