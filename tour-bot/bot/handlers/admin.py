from datetime import datetime
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import BookingStatus
from bot.db.repo import add_tour, set_booking_status
from bot.filters import IsAdmin
from bot.keyboards import AdminCb
from bot.texts import t

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class AddTour(StatesGroup):
    title = State()
    description = State()
    price = State()
    date = State()
    seats = State()


@router.message(Command("admin"))
async def admin_help(message: Message) -> None:
    await message.answer(
        "Admin buyruqlari:\n"
        "/addtour — yangi tur qo'shish\n"
        "/cancel — joriy amalni bekor qilish\n\n"
        "Yangi bronlar shu chatga tasdiqlash tugmalari bilan keladi."
    )


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")


@router.message(Command("addtour"))
async def addtour_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AddTour.title)
    await message.answer("Tur nomini yozing:")


@router.message(AddTour.title, F.text)
async def addtour_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(AddTour.description)
    await message.answer("Tavsifini yozing (dastur, nimalar kiradi):")


@router.message(AddTour.description, F.text)
async def addtour_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(AddTour.price)
    await message.answer("Bir kishi uchun narx va valyuta (masalan: 450 USD yoki 3500000 UZS):")


@router.message(AddTour.price, F.text)
async def addtour_price(message: Message, state: FSMContext) -> None:
    parts = message.text.split()
    if not parts or not parts[0].isdigit():
        await message.answer("Narxni raqam bilan yozing, masalan: 450 USD")
        return
    currency = parts[1].upper() if len(parts) > 1 else "USD"
    await state.update_data(price=int(parts[0]), currency=currency)
    await state.set_state(AddTour.date)
    await message.answer("Boshlanish sanasi (KK.OO.YYYY) yoki '-' agar sana kelishilsa:")


@router.message(AddTour.date, F.text)
async def addtour_date(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if text == "-":
        start = None
    else:
        try:
            start = datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            await message.answer("Sana formati: 15.11.2026 yoki '-'")
            return
    await state.update_data(start_date=start.isoformat() if start else None)
    await state.set_state(AddTour.seats)
    await message.answer("Joylar soni:")


@router.message(AddTour.seats, F.text)
async def addtour_seats(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.text.strip().isdigit():
        await message.answer("Joylar sonini raqam bilan yozing.")
        return
    data = await state.get_data()
    await state.clear()
    start = datetime.fromisoformat(data["start_date"]).date() if data["start_date"] else None
    tour = await add_tour(
        session,
        title=data["title"],
        description=data["description"],
        price=data["price"],
        currency=data["currency"],
        start_date=start,
        seats=int(message.text.strip()),
    )
    await message.answer(f"✅ Tur qo'shildi: #{tour.id} {escape(tour.title)}")


@router.callback_query(AdminCb.filter())
async def decide_booking(callback: CallbackQuery, callback_data: AdminCb, session: AsyncSession, bot: Bot) -> None:
    status = BookingStatus.CONFIRMED if callback_data.action == "ok" else BookingStatus.REJECTED
    booking = await set_booking_status(session, callback_data.booking_id, status)
    if booking is None:
        await callback.answer("Bu bron allaqachon ko'rib chiqilgan.", show_alert=True)
        return
    mark = "✅ TASDIQLANDI" if status == BookingStatus.CONFIRMED else "❌ RAD ETILDI"
    await callback.message.edit_text(f"{escape(callback.message.text)}\n\n{mark} ({escape(callback.from_user.full_name)})")
    key = "booking_confirmed_user" if status == BookingStatus.CONFIRMED else "booking_rejected_user"
    await bot.send_message(booking.user.tg_id, t(booking.user.lang, key, id=booking.id, title=escape(booking.tour.title)))
    await callback.answer()
