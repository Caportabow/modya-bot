from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from config import PRODUCTION, DEVELOPERS_ID

class MaintenanceMiddleware(BaseMiddleware):
    def __init__(self, notify: bool = True, block_module: bool = False):
        super().__init__()
        self.notify = notify
        self.block_module = block_module

    async def __call__(self, handler, event, data):
        # Если на проде — пропускаем всех
        if PRODUCTION and not self.block_module:
            return await handler(event, data)

        # Если пользователь админ — пропускаем
        user_id = getattr(getattr(event, "from_user", None), "id", None)
        if user_id in DEVELOPERS_ID:
            return await handler(event, data)

        # Уведомляем юзера
        if self.notify:
            note = "🛠 Этот модуль сейчас на техобслуживании. Пожалуйста, попробуйте позже."
            if isinstance(event, Message):
                await event.reply(note)
            elif isinstance(event, CallbackQuery):
                await event.answer(note, show_alert=True)

        # Блокируем дальнейшее выполнение
        return None
