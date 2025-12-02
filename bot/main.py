import asyncio
from aiogram import Bot, Dispatcher

from config import TELEGRAM_TOKEN
from handlers import routers
from middlewares import middlewares
import db
import scheduler

# TODO: обновленные рп команды: изменить то, как мы хандлим аргументы в рп командах ++ функция из test.py
# TODO: обновленные варны: время для них, новая команда -- амнистия
# TODO: обновленная чистка: запрашиваем норму, запрашиваем неактив, запрашиваем день недели, в который будет чистка. Новая команда -- чистка. В инфе о юзере теперь указываем примерное количество соо к чистке.
# TODO: обновленные цитаты: новая команда -- /qs чтобы добавить любой стик в список группы. Новая команда -- /qd, чтобы удалить цитату из списка группы

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
