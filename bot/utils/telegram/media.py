import aiohttp
import filetype
import io
from PIL import Image

from aiogram import Bot
from aiogram.types import Message, UserProfilePhotos

from config import TELEGRAM_TOKEN

async def get_file_bytes(bot: Bot, file_id: str) -> bytes:
    file = await bot.get_file(file_id)

    async with aiohttp.ClientSession() as sess:
        url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file.file_path}"
        async with sess.get(url) as resp:
            resp.raise_for_status()
            bytes = await resp.read()
    return bytes

async def image_bytes_to_webp(image_bytes: bytes, quality: int = 80) -> bytes:
    input_buffer = io.BytesIO(image_bytes)
    output_buffer = io.BytesIO()

    with Image.open(input_buffer) as img:
        # если есть альфа — сохраняем
        img.save(
            output_buffer,
            format="WEBP",
            quality=quality,
            method=6  # максимальное сжатие без потери качества
        )

    return output_buffer.getvalue()

async def get_mime_type(file_bytes: bytes) -> str | None:
    kind = filetype.guess(file_bytes)
    if kind:
        return kind.mime
    return None

async def get_user_avatar(bot: Bot, user_id: int) -> bytes | None:
    avatar_data: UserProfilePhotos = await bot.get_user_profile_photos(user_id, offset=0, limit=1)
    if avatar_data.total_count == 0: return None

    sizes = avatar_data.photos[0]  # список PhotoSize
    best = max(sizes, key=lambda p: (p.width or 0) * (p.height or 0))
    bytes = await get_file_bytes(bot, best.file_id)
    return bytes

async def get_quotable_media_id(message: Message) -> dict | None:
    file_id = None
    file_size = 0

    thumb = None

    # 1. Фото — выбираем лучшее по качеству (последнее в списке)
    if message.photo:
        photo = message.photo[-1]
        file_id = photo.file_id
        file_size = photo.file_size

    # 2. Видео
    elif message.video:
        thumb = message.video.thumbnail

    # 3. Гифка (анимация)
    elif message.animation:
        thumb = message.animation.thumbnail

    # 4. Стикер
    elif message.sticker:
        if message.sticker.is_animated or message.sticker.is_video:
            thumb = message.sticker.thumbnail
        else:
            file_id = message.sticker.file_id
            file_size = message.sticker.file_size
    
    # Обрабатываем thumbnail, если есть
    if thumb:
        file_id = thumb.file_id
        file_size = thumb.file_size
    
    if file_id and file_size and file_size <= 10 * 1024 * 1024:  # ≤ 10 МБ
        return {"file_id": file_id, "file_size": file_size}
    
    return None

async def get_message_media(bot, message: Message) -> dict | None:
    media_info = await get_quotable_media_id(message)
    if not media_info: return None

    file_id = media_info["file_id"]
    file_size = media_info["file_size"]

    # Если нашли медиа
    if file_id and file_size and file_size <= 10 * 1024 * 1024:  # ≤ 10 МБ
        file_bytes = await get_file_bytes(bot, file_id)

        # Получаем mime type
        mime_type = await get_mime_type(file_bytes)
        if not mime_type: return None

        return {"source": file_bytes, "type": mime_type}
    
    return None
