import filetype

async def get_mime_type(file_bytes: bytes) -> str | None:
    kind = filetype.guess(file_bytes)
    if kind:
        return kind.mime
    return None
