import re
from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.db.models import Booking, User
from bot.db.repo import create_booking, free_seats, get_tour
from bot.keyboards import ConfirmCb, TourCb, admin_booking_kb, confirm_kb, main_menu, phone_kb
from bot.texts import t

router = Router(name="booking")

PHONE_RE = re.compile(r"^\+?\d{9,15}$")


class BookingForm(StatesGroup):
    people = State()
    phone = State()
    confirm = State()


def normalize_phone(raw: str) -> str | None:
    phone = re.sub(r"[\s\-()]", "", raw)
    if not PHONE_RE.match(phone):
        return None
    return phone if phone.startswith("+") else "+" + phone


def admin_text(booking: Booking) -> str:
    user = booking.user
    username = f"@{user.username}" if user.username else "—"
    return (
        f"🆕 Yangi bron #{booking.id}\n\n"
        f"🌍 {escape(booking.tour.title)}\n"
        f"👥 {booking.people} kishi\n"
        f"👤 {escape(user.full_name)} ({username}, id {user.tg_id})\n"
        f"📱 {booking.phone}\n"
        f"💵 {booking.people * booking.tour.price} {booking.tour.currency}"
    )


@router.callback_query(TourCb.filter(F.action == "book"))
async def start_booking(callback: CallbackQuery, callback_data: TourCb, state: FSMContext, session: AsyncSession, lang: str) -> None:
    tour = await get_tour(session, callback_data.tour_id)
    if tour is None or not tour.is_active:
        await callback.answer(t(lang, "tour_not_found"), show_alert=True)
        return
    free = await free_seats(session, tour)
    if free <= 0:
        await callback.answer(t(lang, "no_seats"), show_alert=True)
        return
    await state.set_state(BookingForm.people)
    await state.update_data(tour_id=tour.id)
    await callback.message.answer(t(lang, "ask_people", max=free))
    await callback.answer()


@router.message(BookingForm.people)
async def got_people(message: Message, state: FSMContext, session: AsyncSession, lang: str) -> None:
    data = await state.get_data()
    tour = await get_tour(session, data["tour_id"])
    free = await free_seats(session, tour)
    text = (message.text or "").strip()
    if not text.isdigit() or not 1 <= int(text) <= free:
        await message.answer(t(lang, "bad_people", max=free))
        return
    await state.update_data(people=int(text))
    await state.set_state(BookingForm.phone)
    await message.answer(t(lang, "ask_phone"), reply_markup=phone_kb(lang))


@router.message(BookingForm.phone)
async def got_phone(message: Message, state: FSMContext, session: AsyncSession, lang: str) -> None:
    raw = message.contact.phone_number if message.contact else (message.text or "")
    phone = normalize_phone(raw)
    if phone is None:
        await message.answer(t(lang, "bad_phone"))
        return
    await state.update_data(phone=phone)
    await state.set_state(BookingForm.confirm)
    data = await state.get_data()
    tour = await get_tour(session, data["tour_id"])
    await message.answer("👌", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        t(
            lang,
            "confirm_booking",
            title=escape(tour.title),
            people=data["people"],
            phone=phone,
            total=data["people"] * tour.price,
            currency=tour.currency,
        ),
        reply_markup=confirm_kb(lang),
    )


@router.callback_query(BookingForm.confirm, ConfirmCb.filter())
async def confirm(
    callback: CallbackQuery,
    callback_data: ConfirmCb,
    state: FSMContext,
    session: AsyncSession,
    db_user: User,
    lang: str,
    bot: Bot,
    settings: Settings,
) -> None:
    data = await state.get_data()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    if not callback_data.ok:
        await callback.message.answer(t(lang, "booking_cancelled"), reply_markup=main_menu(lang))
        await callback.answer()
        return

    tour = await get_tour(session, data["tour_id"])
    if tour is None or await free_seats(session, tour) < data["people"]:
        await callback.message.answer(t(lang, "no_seats"), reply_markup=main_menu(lang))
        await callback.answer()
        return

    booking = await create_booking(session, db_user, tour, data["people"], data["phone"])
    await callback.message.answer(t(lang, "booking_sent", id=booking.id), reply_markup=main_menu(lang))
    await callback.answer()
    for admin_id in settings.admin_ids:
        await bot.send_message(admin_id, admin_text(booking), reply_markup=admin_booking_kb(booking.id))
