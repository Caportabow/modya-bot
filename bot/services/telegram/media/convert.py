import io
from PIL import Image

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
