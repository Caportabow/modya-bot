import asyncio
from aiogram import Bot

from db.warnings import expire_warnings
from .rests import rests
from .cleaning import run_scheduled_cleanings

async def scheduler(bot: Bot):
    print("⚙️ Scheduler started...")
    while True:
        # Выполняем задачи
        await rests(bot)
        await expire_warnings()
        await run_scheduled_cleanings(bot)

        wait_seconds = 60
        await asyncio.sleep(wait_seconds)

def start(bot: Bot):
    asyncio.create_task(scheduler(bot))
