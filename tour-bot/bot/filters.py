from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, TelegramObject, User
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.notify import admin_group_id


class IsAdmin(BaseFilter):
    """Admins from ADMIN_IDS; for button presses, also anyone in the admin group."""

    async def __call__(
        self, event: TelegramObject, event_from_user: User | None, settings: Settings, session: AsyncSession
    ) -> bool:
        if event_from_user is not None and event_from_user.id in settings.admin_ids:
            return True
        if isinstance(event, CallbackQuery) and event.message is not None:
            return event.message.chat.id == await admin_group_id(session, settings)
        return False
