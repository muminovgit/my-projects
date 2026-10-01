"""Free-text messages go to the AI assistant; interested clients become leads for the admin."""
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.ai import AIService
from bot.config import Settings
from bot.db.models import Lead, User
from bot.db.repo import add_chat_messages, chat_history, create_lead, recent_lead_exists
from bot.handlers.booking import normalize_phone
from bot.texts import all_variants, t

log = logging.getLogger(__name__)
router = Router(name="ai_chat")


TELEGRAM_LIMIT = 4000


def split_message(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Split a long AI reply into Telegram-sized parts, preferring paragraph breaks."""
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    return parts + [text] if text else parts


def lead_text(lead: Lead, question: str | None = None) -> str:
    user = lead.user
    username = f"@{user.username}" if user.username else "—"
    text = (
        f"🔥 Yangi lead #{lead.id}\n\n"
        f"👤 {escape(user.full_name)} ({username}, id {user.tg_id})\n"
        f"📱 {lead.phone or 'raqam berilmagan'}\n"
        f"🌐 Til: {user.lang}\n\n"
        f"📝 {escape(lead.summary)}"
    )
    if question:
        text += f"\n\n💬 Oxirgi xabar: {escape(question)}"
    return text


async def notify_lead(bot: Bot, settings: Settings, lead: Lead, question: str | None = None) -> None:
    for admin_id in settings.admin_ids:
        await bot.send_message(admin_id, lead_text(lead, question))


@router.message(F.text.in_(all_variants("btn_ask")))
async def ask(message: Message, lang: str) -> None:
    await message.answer(t(lang, "ask_prompt"))


@router.message(StateFilter(None), F.text & ~F.text.startswith("/") | F.contact)
async def chat(
    message: Message,
    session: AsyncSession,
    db_user: User,
    lang: str,
    bot: Bot,
    settings: Settings,
    ai: AIService | None,
) -> None:
    if message.contact:
        text = f"{message.contact.phone_number}"
    else:
        text = message.text

    if ai is None:
        lead = await create_lead(session, db_user, "Mijoz savol yubordi (AI o'chiq)", normalize_phone(text))
        await notify_lead(bot, settings, lead, text)
        await message.answer(t(lang, "ai_off"))
        return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    history = await chat_history(session, db_user)
    try:
        result = await ai.answer(lang, history, text)
    except Exception:
        log.exception("AI answer failed")
        lead = await create_lead(session, db_user, "AI javob bera olmadi, mijozga menejer javob bersin", None)
        await notify_lead(bot, settings, lead, text)
        await message.answer(t(lang, "ai_error"))
        return

    await add_chat_messages(session, db_user, ("user", text), ("assistant", result.reply))
    for chunk in split_message(result.reply):
        await message.answer(chunk, parse_mode=None)

    if not result.is_lead:
        return
    phone = normalize_phone(result.phone) if result.phone else None
    new_phone = phone is not None and phone != db_user.phone
    # one lead per conversation window, plus a fresh one when the client finally shares a phone
    if new_phone or not await recent_lead_exists(session, db_user):
        lead = await create_lead(session, db_user, result.lead_summary or "Mijoz turga qiziqmoqda", phone)
        await notify_lead(bot, settings, lead, text)
