"""End-to-end: feed fake Telegram updates through the real dispatcher."""
from datetime import datetime

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from bot.__main__ import build_dispatcher
from bot.config import Settings
from bot.handlers import admin, booking, start, tours
from bot.db.models import BookingStatus
from bot.db.repo import add_tour, get_booking
from bot.keyboards import AdminCb, ConfirmCb, LangCb, TourCb

USER_ID = 1001
ADMIN_ID = 9001


class FakeSession(BaseSession):
    """Records every API call instead of hitting Telegram."""

    def __init__(self):
        super().__init__()
        self.calls: list[TelegramMethod] = []

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, AnswerCallbackQuery) or method.__returning__ is bool:
            return True
        chat_id = getattr(method, "chat_id", USER_ID) or USER_ID
        return Message(
            message_id=len(self.calls),
            date=datetime.now(),
            chat=Chat(id=chat_id, type="private"),
            text=getattr(method, "text", None) or "x",
        )

    async def stream_content(self, *args, **kwargs):
        yield b""

    async def close(self):
        pass

    def texts_to(self, chat_id):
        return [c.text for c in self.calls if getattr(c, "chat_id", None) == chat_id and getattr(c, "text", None)]


class Harness:
    def __init__(self, sessionmaker):
        self.fake = FakeSession()
        self.bot = Bot("42:TEST", session=self.fake)
        self.settings = Settings(bot_token="42:TEST", admin_ids=[ADMIN_ID], _env_file=None)
        self.dp = build_dispatcher(self.settings, sessionmaker)
        self.update_id = 0

    def _user(self, uid):
        return User(id=uid, is_bot=False, first_name=f"User{uid}", username=f"u{uid}")

    def _msg(self, uid, text=None, **kw):
        return Message(message_id=1, date=datetime.now(), chat=Chat(id=uid, type="private"), from_user=self._user(uid), text=text, **kw)

    async def send(self, text, uid=USER_ID, **kw):
        self.update_id += 1
        await self.dp.feed_update(self.bot, Update(update_id=self.update_id, message=self._msg(uid, text, **kw)))

    async def press(self, data, uid=USER_ID, text="x"):
        self.update_id += 1
        cb = CallbackQuery(
            id=str(self.update_id),
            from_user=self._user(uid),
            chat_instance="ci",
            data=data.pack(),
            message=self._msg(uid, text),
        )
        await self.dp.feed_update(self.bot, Update(update_id=self.update_id, callback_query=cb))


@pytest.fixture
def h(sessionmaker):
    yield Harness(sessionmaker)
    # handler routers are module-level singletons; detach them so the next test can build a fresh dispatcher
    for r in (admin.router, booking.router, start.router, tours.router):
        r._parent_router = None


async def test_full_booking_flow(h, sessionmaker):
    async with sessionmaker() as s:
        tour = await add_tour(s, "Samarqand 3 kun", "Registon", 150, 10)

    await h.send("/start")
    await h.press(LangCb(code="uz"))
    assert any("Assalomu alaykum" in t for t in h.fake.texts_to(USER_ID))

    await h.send("🌍 Turlar")
    await h.press(TourCb(action="show", tour_id=tour.id))
    await h.press(TourCb(action="book", tour_id=tour.id))
    await h.send("abc")
    assert "1 dan 10 gacha" in h.fake.texts_to(USER_ID)[-1]
    await h.send("2")
    await h.send("+998 90 123 45 67")
    assert "300 USD" in h.fake.texts_to(USER_ID)[-1]
    await h.press(ConfirmCb(ok=True))
    assert "#1" in h.fake.texts_to(USER_ID)[-1]

    admin_msgs = h.fake.texts_to(ADMIN_ID)
    assert len(admin_msgs) == 1 and "Samarqand 3 kun" in admin_msgs[0] and "+998901234567" in admin_msgs[0]

    await h.press(AdminCb(action="ok", booking_id=1), uid=ADMIN_ID, text=admin_msgs[0])
    assert "tasdiqlandi" in h.fake.texts_to(USER_ID)[-1]
    async with sessionmaker() as s:
        assert (await get_booking(s, 1)).status == BookingStatus.CONFIRMED


async def test_russian_user_gets_russian_texts(h, sessionmaker):
    await h.send("/start")
    await h.press(LangCb(code="ru"))
    await h.send("🌍 Туры")
    assert h.fake.texts_to(USER_ID)[-1] == "Сейчас нет активных туров."


async def test_non_admin_cannot_add_tour(h, sessionmaker):
    await h.send("/addtour")
    assert not any("Tur nomini" in t for t in h.fake.texts_to(USER_ID))


async def test_admin_adds_tour(h, sessionmaker):
    for text in ["/addtour", "Xiva", "Ichan qal'a", "3500000 UZS", "15.11.2026", "20"]:
        await h.send(text, uid=ADMIN_ID)
    assert "Tur qo'shildi" in h.fake.texts_to(ADMIN_ID)[-1]
    await h.send("🌍 Turlar")
    async with sessionmaker() as s:
        from bot.db.repo import list_active_tours
        tours = await list_active_tours(s)
    assert tours[0].title == "Xiva" and tours[0].currency == "UZS" and tours[0].seats == 20
