from datetime import datetime
from html import escape

import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.ai import AIService, TourDraft
from bot.db.models import BookingStatus, TourCategory
from bot.db.repo import add_tour, set_booking_status, set_setting
from bot.filters import IsAdmin
from bot.notify import ADMIN_GROUP_KEY
from bot.keyboards import AdminCb, AiTourCb, CategoryCb, ai_tour_kb, categories_kb
from bot.texts import t

log = logging.getLogger(__name__)

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class AiTour(StatesGroup):
    preview = State()


class AddTour(StatesGroup):
    category = State()
    title = State()
    description = State()
    price = State()
    date = State()
    seats = State()


@router.message(Command("setgroup"), F.chat.type.in_({"group", "supergroup"}))
async def set_group(message: Message, session: AsyncSession) -> None:
    await set_setting(session, ADMIN_GROUP_KEY, str(message.chat.id))
    await message.answer(
        "✅ Shu guruh admin guruhi qilib belgilandi. Endi yangi leadlar va bronlar shu yerga keladi, "
        "guruh a'zolari bronlarni tasdiqlashi yoki rad etishi mumkin."
    )


@router.message(Command("admin"))
async def admin_help(message: Message) -> None:
    await message.answer(
        "Admin buyruqlari:\n"
        "/addtour — yangi tur qo'shish (qadamma-qadam)\n"
        "/aitour <tavsif> — AI turni o'zi yozib beradi, masalan:\n"
        "  /aitour Dubay 5 kun, 15.11.2026 dan, 650 USD, 20 joy, mehmonxona va aviachipta bilan\n"
        "/cancel — joriy amalni bekor qilish\n"
        "/setgroup — (guruh ichida yozing) leadlar va bronlar shu guruhga keladi\n\n"
        "Guruh ulanmagan bo'lsa, leadlar va bronlar shu chatga keladi."
    )


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")


@router.message(Command("addtour"))
async def addtour_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AddTour.category)
    await message.answer("Tur yo'nalishini tanlang:", reply_markup=categories_kb("uz"))


@router.callback_query(AddTour.category, CategoryCb.filter(F.category != ""))
async def addtour_category(callback: CallbackQuery, callback_data: CategoryCb, state: FSMContext) -> None:
    await state.update_data(category=callback_data.category)
    await state.set_state(AddTour.title)
    await callback.message.edit_text(f"Yo'nalish: {t('uz', 'cat_' + callback_data.category)}")
    await callback.message.answer("Tur nomini yozing (o'zbekcha):")
    await callback.answer()


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
async def addtour_seats(message: Message, state: FSMContext, session: AsyncSession, ai: AIService | None) -> None:
    if not message.text.strip().isdigit():
        await message.answer("Joylar sonini raqam bilan yozing.")
        return
    data = await state.get_data()
    await state.clear()
    translations = {}
    if ai is not None:
        try:
            translations = (await ai.translate(data["title"], data["description"])).model_dump()
        except Exception:
            log.exception("Tour translation failed")
    tour = await add_tour(
        session,
        title=data["title"],
        description=data["description"],
        price=data["price"],
        currency=data["currency"],
        start_date=datetime.fromisoformat(data["start_date"]).date() if data["start_date"] else None,
        seats=int(message.text.strip()),
        category=TourCategory(data["category"]),
        **translations,
    )
    note = " (ruscha va inglizcha tarjimasi bilan)" if translations else ""
    await message.answer(f"✅ Tur qo'shildi{note}: #{tour.id} {escape(tour.title)}")


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
    await bot.send_message(booking.user.tg_id, t(booking.user.lang, key, id=booking.id, title=escape(booking.tour.title_for(booking.user.lang))))
    await callback.answer()


def parse_draft_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None


def draft_preview(draft: TourDraft) -> str:
    return (
        "🤖 AI tayyorlagan tur:\n\n"
        f"Yo'nalish: {t('uz', 'cat_' + draft.category)}\n"
        f"💵 {draft.price} {draft.currency} · 📅 {draft.start_date or 'kelishiladi'} · 🪑 {draft.seats} joy\n\n"
        f"🇺🇿 <b>{escape(draft.title)}</b>\n{escape(draft.description)}\n\n"
        f"🇷🇺 <b>{escape(draft.title_ru)}</b>\n{escape(draft.description_ru)}\n\n"
        f"🇬🇧 <b>{escape(draft.title_en)}</b>\n{escape(draft.description_en)}"
    )


@router.message(Command("aitour"))
async def aitour(message: Message, command: CommandObject, state: FSMContext, bot: Bot, ai: AIService | None) -> None:
    if ai is None:
        await message.answer("AI o'chiq: .env faylida ANTHROPIC_API_KEY yo'q. /addtour dan foydalaning.")
        return
    if not command.args:
        await message.answer("Turni qisqacha yozing, masalan:\n/aitour Dubay 5 kun, 15.11.2026, 650 USD, 20 joy")
        return
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        draft = await ai.draft_tour(command.args)
    except Exception:
        log.exception("AI tour draft failed")
        await message.answer("AI turni yarata olmadi. Qayta urinib ko'ring yoki /addtour dan foydalaning.")
        return
    if draft.category not in {c.value for c in TourCategory}:
        draft.category = TourCategory.DOMESTIC.value
    await state.set_state(AiTour.preview)
    await state.update_data(draft=draft.model_dump())
    text = draft_preview(draft)
    if len(text) > 4000:
        text = text[:4000] + "…"
    await message.answer(text, reply_markup=ai_tour_kb())


@router.callback_query(AiTour.preview, AiTourCb.filter())
async def aitour_decide(callback: CallbackQuery, callback_data: AiTourCb, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    if not callback_data.save:
        await callback.message.answer("Bekor qilindi.")
        await callback.answer()
        return
    draft = TourDraft(**data["draft"])
    tour = await add_tour(
        session,
        title=draft.title,
        description=draft.description,
        price=draft.price,
        currency=draft.currency.upper(),
        start_date=parse_draft_date(draft.start_date),
        seats=draft.seats,
        category=TourCategory(draft.category),
        title_ru=draft.title_ru,
        description_ru=draft.description_ru,
        title_en=draft.title_en,
        description_en=draft.description_en,
    )
    await callback.message.answer(f"✅ Tur saqlandi: #{tour.id} {escape(tour.title)}")
    await callback.answer()
