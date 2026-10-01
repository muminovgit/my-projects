"""Where admin notifications (leads, bookings) go: the admin group if one is set, else each admin's DM."""
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.db.repo import get_setting

log = logging.getLogger(__name__)

ADMIN_GROUP_KEY = "admin_group_id"


async def admin_group_id(session: AsyncSession, settings: Settings) -> int | None:
    saved = await get_setting(session, ADMIN_GROUP_KEY)
    return int(saved) if saved else settings.admin_group_id


async def notify_admins(
    bot: Bot,
    session: AsyncSession,
    settings: Settings,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    group_id = await admin_group_id(session, settings)
    if group_id is not None:
        try:
            await bot.send_message(group_id, text, reply_markup=reply_markup)
            return
        except Exception:
            # e.g. the bot was removed from the group: don't lose the lead, fall back to DMs
            log.exception("Could not post to admin group %s, falling back to admin DMs", group_id)
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except Exception:
            log.exception("Could not notify admin %s", admin_id)
