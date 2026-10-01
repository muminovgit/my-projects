from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.repo import get_or_create_user


class DbSessionMiddleware(BaseMiddleware):
    """Opens a DB session per update and injects `session`, `db_user` and `lang`."""

    def __init__(self, sessionmaker: async_sessionmaker):
        self.sessionmaker = sessionmaker

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.sessionmaker() as session:
            data["session"] = session
            tg_user = data.get("event_from_user")
            if tg_user is not None:
                user = await get_or_create_user(session, tg_user.id, tg_user.full_name, tg_user.username)
                data["db_user"] = user
                data["lang"] = user.lang
            return await handler(event, data)
