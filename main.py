import asyncio
from telethon import TelegramClient
from aiogram import Bot, Dispatcher

from config import TOKEN, API_ID, API_HASH
from handlers import routers
from middlewares import middlewares
import db

# TODO: системные сообщения
# TODO: больше картинок в описание команд
# TODO: +рест/-рест
# TODO: система браков
# TODO: Docker

telethon_client = TelegramClient("bot", API_ID, API_HASH)
dp = Dispatcher()
bot = Bot(token=TOKEN)


async def main():
    # регистрируем роутеры и мидлвари
    for router in routers:
        dp.include_router(router)
    for middleware in middlewares:
        dp.message.middleware(middleware)

    await telethon_client.start(bot_token=TOKEN)

    await db.init_db()
    try:
        await dp.start_polling(bot,
                    allowed_updates=dp.resolve_used_update_types(),
                    telethon_client=telethon_client
        )
    finally:
        await db.close_db()

if __name__ == "__main__":
    asyncio.run(main())
