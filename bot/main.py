import asyncio
from aiogram import Bot, Dispatcher

from config import TELEGRAM_TOKEN
from handlers import routers
from middlewares import middlewares
import db
import scheduler

# TODO: переработать sendm и sendu чтобы можно было выложить на гит
# TODO: обновление рп команд: изменить то, как мы хандлим аргументы в рп командах ++ функция из test.py
# TODO: указывать в user_info сколько у него будет соо к чистке
# TODO: время для варнов
# TODO: амнистия для варнов
# TODO: обновленная чистка - запоминание нормы и неактива в chats
# TODO: планирование чистки

# TODO: стикерпаки для quotes
# TODO: возможность удалить цитату

dp = Dispatcher()
bot = Bot(token=TELEGRAM_TOKEN)


async def main():
    # регистрируем роутеры и мидлвари
    for router in routers:
        dp.include_router(router)
    for middleware in middlewares:
        dp.message.middleware(middleware)

    await db.init_db()
    scheduler.start(bot)
    try:
        print("🤖 Bot started...")
        await dp.start_polling(bot,
                    allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        await db.close_db()

if __name__ == "__main__":
    asyncio.run(main())
