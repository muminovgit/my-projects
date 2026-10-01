from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Tour
from bot.db.repo import free_seats, get_tour, list_active_tours
from bot.keyboards import TourCb, tour_kb, tours_kb
from bot.texts import all_variants, t

router = Router(name="tours")


def format_tour(lang: str, tour: Tour, free: int) -> str:
    return t(
        lang,
        "tour_card",
        title=escape(tour.title),
        description=escape(tour.description),
        price=tour.price,
        currency=tour.currency,
        date=tour.start_date.strftime("%d.%m.%Y") if tour.start_date else t(lang, "date_tbd"),
        free=max(free, 0),
    )


@router.message(F.text.in_(all_variants("btn_tours")))
async def show_tours(message: Message, session: AsyncSession, lang: str) -> None:
    tours = await list_active_tours(session)
    if not tours:
        await message.answer(t(lang, "no_tours"))
        return
    await message.answer(t(lang, "tours_title"), reply_markup=tours_kb(tours))


@router.callback_query(TourCb.filter(F.action == "list"))
async def back_to_list(callback: CallbackQuery, session: AsyncSession, lang: str) -> None:
    tours = await list_active_tours(session)
    text = t(lang, "tours_title") if tours else t(lang, "no_tours")
    await callback.message.edit_text(text, reply_markup=tours_kb(tours))
    await callback.answer()


@router.callback_query(TourCb.filter(F.action == "show"))
async def show_tour(callback: CallbackQuery, callback_data: TourCb, session: AsyncSession, lang: str) -> None:
    tour = await get_tour(session, callback_data.tour_id)
    if tour is None or not tour.is_active:
        await callback.answer(t(lang, "tour_not_found"), show_alert=True)
        return
    free = await free_seats(session, tour)
    await callback.message.edit_text(format_tour(lang, tour, free), reply_markup=tour_kb(lang, tour.id, free > 0))
    await callback.answer()
