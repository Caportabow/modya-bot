import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from config import TELEGRAM_TOKEN
from routers import routers
from middlewares import middlewares
import db
from services import scheduler


# Настройка логирования
def _setup_logging() -> None:
    """
    Настраивает формат и уровень логирования для приложения.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


_setup_logging()


def create_bot(token: str = TELEGRAM_TOKEN) -> Bot:
    """
    Создаёт экземпляр бота с заданным токеном.

    Args:
        token: Токен Telegram-бота.

    Returns:
        Экземпляр Bot.
    """
    return Bot(token=token)


dp = Dispatcher()
bot = create_bot()


async def _register_routers_and_middlewares(dp: Dispatcher) -> None:
    """
    Регистрирует все роутеры и мидлвари в диспетчере.

    Args:
        dp: Экземпляр Dispatcher.
    """
    for router in routers:
        dp.include_router(router)
    for middleware in middlewares:
        dp.message.middleware(middleware)


async def main() -> None:
    """
    Основная асинхронная функция запуска бота.

    Выполняет инициализацию базы данных, запуск планировщика задач
    и запуск polling-режима бота.
    """
    await _register_routers_and_middlewares(dp)

    await db.init_db()
    scheduler.start(bot)

    try:
        logging.info("🤖 Bot started...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        await db.close_db()


if __name__ == "__main__":
    asyncio.run(main())
