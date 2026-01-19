import aiohttp
from aiogram import Bot

from config import TELEGRAM_TOKEN

async def fetch_bytes(bot: Bot, file_id: str) -> bytes:
    file = await bot.get_file(file_id)

    async with aiohttp.ClientSession() as sess:
        url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file.file_path}"
        async with sess.get(url) as resp:
            resp.raise_for_status()
            bytes = await resp.read()
    return bytes
