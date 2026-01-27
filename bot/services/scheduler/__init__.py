import asyncio
import logging
from aiogram import Bot

from services.scheduler.jobs.cleaning import run_cleanings
from services.scheduler.jobs.rests import expire_rests
from services.scheduler.jobs.warnings import expire_warnings

async def scheduler(bot: Bot):
    logging.info("⚙️ Scheduler started...")
    while True:
        # Выполняем задачи
        await expire_rests(bot)
        await expire_warnings()
        await run_cleanings(bot)

        wait_seconds = 60
        await asyncio.sleep(wait_seconds)

def start(bot: Bot):
    asyncio.create_task(scheduler(bot))
