from html import escape

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User
from bot.db.repo import set_user_lang, user_bookings
from bot.keyboards import LangCb, lang_kb, main_menu
from bot.texts import all_variants, t

router = Router(name="start")
router.message.filter(F.chat.type == "private")


@router.message(CommandStart())
async def cmd_start(message: Message, lang: str) -> None:
    await message.answer(t(lang, "choose_lang"), reply_markup=lang_kb())


@router.message(F.text.in_(all_variants("btn_lang")))
async def change_lang(message: Message, lang: str) -> None:
    await message.answer(t(lang, "choose_lang"), reply_markup=lang_kb())


@router.callback_query(LangCb.filter())
async def lang_chosen(callback: CallbackQuery, callback_data: LangCb, session: AsyncSession, db_user: User) -> None:
    lang = callback_data.code
    await set_user_lang(session, db_user.tg_id, lang)
    await callback.message.delete()
    await callback.message.answer(t(lang, "welcome", name=escape(db_user.full_name)), reply_markup=main_menu(lang))
    await callback.answer(t(lang, "lang_set"))


@router.message(F.text.in_(all_variants("btn_contacts")))
async def contacts(message: Message, lang: str) -> None:
    await message.answer(t(lang, "contacts"))


@router.message(F.text.in_(all_variants("btn_my_bookings")))
async def my_bookings(message: Message, session: AsyncSession, lang: str) -> None:
    bookings = await user_bookings(session, message.from_user.id)
    if not bookings:
        await message.answer(t(lang, "no_bookings"))
        return
    lines = [t(lang, "my_bookings_title")]
    for b in bookings:
        lines.append(f"#{b.id} · {escape(b.tour.title_for(lang))} · {b.people} · {t(lang, 'status_' + b.status.value)}")
    await message.answer("\n".join(lines))
