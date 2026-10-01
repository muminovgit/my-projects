from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.models import Tour
from bot.texts import t


class LangCb(CallbackData, prefix="lang"):
    code: str


class TourCb(CallbackData, prefix="tour"):
    action: str  # "show" | "book" | "list"
    tour_id: int = 0


class ConfirmCb(CallbackData, prefix="confirm"):
    ok: bool


class AdminCb(CallbackData, prefix="adm"):
    action: str  # "ok" | "no"
    booking_id: int


def lang_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🇺🇿 O'zbekcha", callback_data=LangCb(code="uz"))
    b.button(text="🇷🇺 Русский", callback_data=LangCb(code="ru"))
    return b.as_markup()


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_tours"))],
            [KeyboardButton(text=t(lang, "btn_my_bookings")), KeyboardButton(text=t(lang, "btn_contacts"))],
            [KeyboardButton(text=t(lang, "btn_lang"))],
        ],
        resize_keyboard=True,
    )


def tours_kb(tours: list[Tour]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for tour in tours:
        b.button(text=f"{tour.title} · {tour.price} {tour.currency}", callback_data=TourCb(action="show", tour_id=tour.id))
    b.adjust(1)
    return b.as_markup()


def tour_kb(lang: str, tour_id: int, can_book: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if can_book:
        b.button(text=t(lang, "btn_book"), callback_data=TourCb(action="book", tour_id=tour_id))
    b.button(text=t(lang, "btn_back"), callback_data=TourCb(action="list"))
    b.adjust(1)
    return b.as_markup()


def phone_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "btn_send_phone"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t(lang, "btn_confirm"), callback_data=ConfirmCb(ok=True))
    b.button(text=t(lang, "btn_cancel"), callback_data=ConfirmCb(ok=False))
    return b.as_markup()


def admin_booking_kb(booking_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Tasdiqlash", callback_data=AdminCb(action="ok", booking_id=booking_id))
    b.button(text="❌ Rad etish", callback_data=AdminCb(action="no", booking_id=booking_id))
    return b.as_markup()
