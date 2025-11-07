import asyncio
from telethon import TelegramClient
from aiogram import Bot, Dispatcher

from config import TELEGRAM_TOKEN, API_ID, API_HASH
from handlers import routers
from middlewares import middlewares
import db

# DONE: новая команда - неактив {период}. Лидерборд вместо фиксированных значений [день|неделя|месяц|год|вся] теперь поддерживает любой заданный вами период. Теперь для чистки боту нужно быть минимум неделю в чате, в чистке не учитываются вышедшие пользователи, устранён баг где время отправки цитаты закрывало её содержание. Несколько новых РП команд, улучшено отображение данных  
# TODO: системные сообщения
# TODO: больше картинок в описание команд
# TODO: +рест/-рест
# TODO: система браков

telethon_client = TelegramClient("bot", API_ID, API_HASH)
dp = Dispatcher()
bot = Bot(token=TELEGRAM_TOKEN)


async def main():
    # регистрируем роутеры и мидлвари
    for router in routers:
        dp.include_router(router)
    for middleware in middlewares:
        dp.message.middleware(middleware)

    await telethon_client.start(bot_token=TELEGRAM_TOKEN)

    await db.init_db()
    try:
        print("🤖 Bot started...")
        await dp.start_polling(bot,
                    allowed_updates=dp.resolve_used_update_types(),
                    telethon_client=telethon_client
        )
    finally:
        await db.close_db()

if __name__ == "__main__":
    asyncio.run(main())
