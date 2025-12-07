import asyncio
from aiogram import Bot
from datetime import timedelta

from db.warnings import expire_warnings

from .rests import rests

async def scheduler(bot: Bot):
    print("⚙️ Scheduler started...")
    while True:
        # Выполняем задачи
        await rests(bot)
        await expire_warnings()

        wait_seconds = timedelta(hours=3).total_seconds()
        await asyncio.sleep(wait_seconds)

def start(bot: Bot):
    asyncio.create_task(scheduler(bot))
