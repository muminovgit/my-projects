from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Tour, TourCategory
from bot.db.repo import free_seats, get_tour, list_active_tours
from bot.keyboards import CategoryCb, TourCb, categories_kb, tour_kb, tours_kb
from bot.texts import all_variants, t

router = Router(name="tours")
router.message.filter(F.chat.type == "private")


def format_tour(lang: str, tour: Tour, free: int) -> str:
    return t(
        lang,
        "tour_card",
        title=escape(tour.title_for(lang)),
        description=escape(tour.description_for(lang)),
        price=tour.price,
        currency=tour.currency,
        date=tour.start_date.strftime("%d.%m.%Y") if tour.start_date else t(lang, "date_tbd"),
        free=max(free, 0),
    )


@router.message(F.text.in_(all_variants("btn_tours")))
async def show_categories(message: Message, lang: str) -> None:
    await message.answer(t(lang, "choose_category"), reply_markup=categories_kb(lang))


@router.callback_query(CategoryCb.filter())
async def show_category(callback: CallbackQuery, callback_data: CategoryCb, session: AsyncSession, lang: str) -> None:
    if not callback_data.category:
        await callback.message.edit_text(t(lang, "choose_category"), reply_markup=categories_kb(lang))
        await callback.answer()
        return
    category = TourCategory(callback_data.category)
    tours = await list_active_tours(session, category)
    text = f"{t(lang, 'cat_' + category.value)}\n\n" + (t(lang, "tours_title") if tours else t(lang, "no_tours"))
    await callback.message.edit_text(text, reply_markup=tours_kb(lang, tours))
    await callback.answer()


@router.callback_query(TourCb.filter(F.action == "show"))
async def show_tour(callback: CallbackQuery, callback_data: TourCb, session: AsyncSession, lang: str) -> None:
    tour = await get_tour(session, callback_data.tour_id)
    if tour is None or not tour.is_active:
        await callback.answer(t(lang, "tour_not_found"), show_alert=True)
        return
    free = await free_seats(session, tour)
    await callback.message.edit_text(format_tour(lang, tour, free), reply_markup=tour_kb(lang, tour, free > 0))
    await callback.answer()
