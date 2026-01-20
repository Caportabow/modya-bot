from db.warnings import expire_warnings as _expire_warnings

async def expire_warnings():
    """Истекает варны, срок которых закончился."""
    await _expire_warnings()
