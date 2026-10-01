"""End-to-end: feed fake Telegram updates through the real dispatcher."""
from datetime import datetime

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from bot.__main__ import build_dispatcher
from bot.config import Settings
from bot.ai import AssistantReply, TourDraft, Translation
from bot.handlers import admin, ai_chat, booking, start, tours
from bot.db.models import BookingStatus, Lead, TourCategory
from bot.db.repo import add_tour, get_booking, list_active_tours
from bot.keyboards import AdminCb, AiTourCb, CategoryCb, ConfirmCb, LangCb, TourCb
from sqlalchemy import select

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
        ).as_(bot)

    async def stream_content(self, *args, **kwargs):
        yield b""

    async def close(self):
        pass

    def texts_to(self, chat_id):
        return [c.text for c in self.calls if getattr(c, "chat_id", None) == chat_id and getattr(c, "text", None)]


class FakeAI:
    def __init__(self):
        self.next_reply = AssistantReply(reply="Javob", is_lead=False)
        self.calls = []

    async def answer(self, lang, history, text):
        self.calls.append((lang, [(m.role, m.content) for m in history], text))
        return self.next_reply

    async def draft_tour(self, request):
        return TourDraft(
            category="abroad", title="Dubay 5 kun", description="Tavsif", title_ru="Дубай 5 дней", description_ru="Описание",
            title_en="Dubai 5 days", description_en="Description", price=650, currency="usd", start_date="15.11.2026", seats=20,
        )

    async def translate(self, title, description):
        return Translation(title_ru=f"{title} RU", description_ru="RU", title_en=f"{title} EN", description_en="EN")


class Harness:
    def __init__(self, sessionmaker, ai=None):
        self.fake = FakeSession()
        self.bot = Bot("42:TEST", session=self.fake)
        self.settings = Settings(bot_token="42:TEST", admin_ids=[ADMIN_ID], _env_file=None)
        self.ai = ai
        self.dp = build_dispatcher(self.settings, sessionmaker, ai)
        self.update_id = 0

    def _user(self, uid):
        return User(id=uid, is_bot=False, first_name=f"User{uid}", username=f"u{uid}")

    def _msg(self, uid, text=None, chat_id=None, **kw):
        chat = Chat(id=chat_id, type="supergroup") if chat_id else Chat(id=uid, type="private")
        return Message(message_id=1, date=datetime.now(), chat=chat, from_user=self._user(uid), text=text, **kw)

    async def send(self, text, uid=USER_ID, **kw):
        self.update_id += 1
        await self.dp.feed_update(self.bot, Update(update_id=self.update_id, message=self._msg(uid, text, **kw)))

    async def press(self, data, uid=USER_ID, text="x", chat_id=None):
        self.update_id += 1
        cb = CallbackQuery(
            id=str(self.update_id),
            from_user=self._user(uid),
            chat_instance="ci",
            data=data.pack(),
            message=self._msg(uid, text, chat_id=chat_id),
        )
        await self.dp.feed_update(self.bot, Update(update_id=self.update_id, callback_query=cb))


def _detach_routers():
    # handler routers are module-level singletons; detach them so the next test can build a fresh dispatcher
    for r in (admin.router, ai_chat.router, booking.router, start.router, tours.router):
        r._parent_router = None


@pytest.fixture
def h(sessionmaker):
    yield Harness(sessionmaker)
    _detach_routers()


@pytest.fixture
def hai(sessionmaker):
    yield Harness(sessionmaker, FakeAI())
    _detach_routers()


async def test_full_booking_flow(h, sessionmaker):
    async with sessionmaker() as s:
        tour = await add_tour(s, "Samarqand 3 kun", "Registon", 150, 10, category=TourCategory.DOMESTIC)

    await h.send("/start")
    await h.press(LangCb(code="uz"))
    assert any("Assalomu alaykum" in t for t in h.fake.texts_to(USER_ID))

    await h.send("🌍 Turlar")
    assert "yo'nalish" in h.fake.texts_to(USER_ID)[-1]
    await h.press(CategoryCb(category="domestic"))
    await h.press(TourCb(action="show", tour_id=tour.id))
    assert "Registon" in h.fake.texts_to(USER_ID)[-1]
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
    await h.press(CategoryCb(category="abroad"))
    assert h.fake.texts_to(USER_ID)[-1].endswith("Сейчас нет активных туров.")


async def test_english_user_sees_translated_tour(h, sessionmaker):
    async with sessionmaker() as s:
        tour = await add_tour(s, "Xiva", "Ichan qal'a", 100, 5, title_en="Khiva", description_en="Old town")
    await h.send("/start")
    await h.press(LangCb(code="en"))
    await h.send("🌍 Tours")
    await h.press(TourCb(action="show", tour_id=tour.id))
    card = h.fake.texts_to(USER_ID)[-1]
    assert "Khiva" in card and "Old town" in card and "Free seats" in card


async def test_non_admin_cannot_add_tour(h, sessionmaker):
    await h.send("/addtour")
    assert not any("Tur nomini" in t for t in h.fake.texts_to(USER_ID))


async def test_admin_adds_tour(h, sessionmaker):
    await h.send("/addtour", uid=ADMIN_ID)
    await h.press(CategoryCb(category="pilgrimage"), uid=ADMIN_ID)
    for text in ["Umra 14 kun", "Makka va Madina", "1500 USD", "15.11.2026", "20"]:
        await h.send(text, uid=ADMIN_ID)
    assert "Tur qo'shildi" in h.fake.texts_to(ADMIN_ID)[-1]
    async with sessionmaker() as s:
        tours = await list_active_tours(s, TourCategory.PILGRIMAGE)
    assert tours[0].title == "Umra 14 kun" and tours[0].currency == "USD" and tours[0].seats == 20
    assert tours[0].title_ru is None  # no AI configured, no translation


async def test_admin_tour_gets_ai_translation(hai, sessionmaker):
    await hai.send("/addtour", uid=ADMIN_ID)
    await hai.press(CategoryCb(category="domestic"), uid=ADMIN_ID)
    for text in ["Xiva", "Ichan qal'a", "100 USD", "-", "5"]:
        await hai.send(text, uid=ADMIN_ID)
    async with sessionmaker() as s:
        tour = (await list_active_tours(s))[0]
    assert tour.title_ru == "Xiva RU" and tour.title_en == "Xiva EN" and tour.start_date is None


async def test_aitour_creates_tour_after_admin_saves(hai, sessionmaker):
    await hai.send("/aitour Dubay 5 kun 650 USD 20 joy", uid=ADMIN_ID)
    assert "Dubai 5 days" in hai.fake.texts_to(ADMIN_ID)[-1]
    async with sessionmaker() as s:
        assert await list_active_tours(s) == []
    await hai.press(AiTourCb(save=True), uid=ADMIN_ID)
    async with sessionmaker() as s:
        tour = (await list_active_tours(s, TourCategory.ABROAD))[0]
    assert tour.title_en == "Dubai 5 days" and tour.currency == "USD" and tour.start_date.year == 2026


async def test_ai_answers_and_sends_lead_once(hai, sessionmaker):
    await hai.send("Samarqandga tur bormi?")
    assert hai.fake.texts_to(USER_ID)[-1] == "Javob"
    assert hai.fake.texts_to(ADMIN_ID) == []

    hai.ai.next_reply = AssistantReply(reply="Raqamingizni yuboring", is_lead=True, lead_summary="Samarqandga 2 kishi")
    await hai.send("2 kishi bormoqchimiz")
    assert "Samarqandga 2 kishi" in hai.fake.texts_to(ADMIN_ID)[-1]
    # the lead goes only to the admin; the client sees just the reply
    assert not any("lead" in t.lower() or "Samarqandga 2 kishi" in t for t in hai.fake.texts_to(USER_ID))
    # history is passed back to the model
    assert hai.ai.calls[1][1] == [("user", "Samarqandga tur bormi?"), ("assistant", "Javob")]

    await hai.send("yana bir savol")  # still a lead, but already reported
    assert len(hai.fake.texts_to(ADMIN_ID)) == 1

    hai.ai.next_reply = AssistantReply(reply="Rahmat", is_lead=True, phone="+998 90 111 22 33", lead_summary="Raqam berdi")
    await hai.send("+998 90 111 22 33")
    admin_msgs = hai.fake.texts_to(ADMIN_ID)
    assert len(admin_msgs) == 2 and "+998901112233" in admin_msgs[-1]


async def test_without_ai_questions_go_to_admin(h, sessionmaker):
    await h.send("Dubayga viza kerakmi?")
    assert "menejerga" in h.fake.texts_to(USER_ID)[-1]
    assert "Dubayga viza kerakmi?" in h.fake.texts_to(ADMIN_ID)[-1]
    async with sessionmaker() as s:
        assert len(list(await s.scalars(select(Lead)))) == 1


async def test_long_ai_reply_is_split(hai, sessionmaker):
    hai.ai.next_reply = AssistantReply(reply=("1-kun: Dubay bo'ylab sayohat.\n" * 400).strip())
    await hai.send("Dubayga 7 kunlik tur tuzib bering")
    parts = hai.fake.texts_to(USER_ID)
    assert len(parts) > 1 and all(len(p) <= 4096 for p in parts)


async def test_wait_note_shown_then_removed(hai, sessionmaker):
    await hai.send("Turkiyaga tur bormi?")
    from aiogram.methods import DeleteMessage
    texts = hai.fake.texts_to(USER_ID)
    assert "🔎" in texts[0] and texts[-1] == "Javob"
    assert any(isinstance(c, DeleteMessage) for c in hai.fake.calls)


async def test_slow_ai_times_out_and_goes_to_admin(hai, sessionmaker, monkeypatch):
    import asyncio

    async def slow(*args):
        await asyncio.sleep(5)

    monkeypatch.setattr(ai_chat, "AI_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(hai.ai, "answer", slow)
    await hai.send("Misrga tur tuzib bering")
    assert "menejerga" in hai.fake.texts_to(USER_ID)[-1]
    assert "Misrga tur tuzib bering" in hai.fake.texts_to(ADMIN_ID)[-1]


GROUP_ID = -100500
MEMBER_ID = 7007  # in the admin group but not in ADMIN_IDS


async def test_admin_group_gets_leads_and_bookings(hai, sessionmaker):
    await hai.send("/setgroup", uid=MEMBER_ID, chat_id=GROUP_ID)  # non-admin: ignored
    assert hai.fake.texts_to(GROUP_ID) == []
    await hai.send("/setgroup", uid=ADMIN_ID, chat_id=GROUP_ID)
    assert "admin guruhi" in hai.fake.texts_to(GROUP_ID)[-1]

    hai.ai.next_reply = AssistantReply(reply="Raqamingizni yuboring", is_lead=True, phone="+998901112233", lead_summary="Dubay, 2 kishi")
    await hai.send("Dubayga boramiz, +998901112233")
    lead = hai.fake.texts_to(GROUP_ID)[-1]
    assert "Dubay, 2 kishi" in lead and "+998901112233" in lead
    assert hai.fake.texts_to(ADMIN_ID) == []

    async with sessionmaker() as s:
        tour = await add_tour(s, "Xiva", "", 100, 10)
    await hai.press(TourCb(action="book", tour_id=tour.id))
    await hai.send("1")
    await hai.send("+998901112233")
    await hai.press(ConfirmCb(ok=True))
    booking_msg = hai.fake.texts_to(GROUP_ID)[-1]
    assert "Yangi bron #1" in booking_msg

    # any member of the admin group can decide
    await hai.press(AdminCb(action="ok", booking_id=1), uid=MEMBER_ID, text=booking_msg, chat_id=GROUP_ID)
    async with sessionmaker() as s:
        assert (await get_booking(s, 1)).status == BookingStatus.CONFIRMED


async def test_bot_ignores_chatter_in_groups(hai, sessionmaker):
    await hai.send("salom hammaga", uid=MEMBER_ID, chat_id=GROUP_ID)
    assert hai.ai.calls == [] and hai.fake.texts_to(GROUP_ID) == []


async def test_admin_group_from_env(sessionmaker):
    harness = Harness(sessionmaker, FakeAI())
    harness.settings.admin_group_id = GROUP_ID
    harness.ai.next_reply = AssistantReply(reply="ok", is_lead=True, lead_summary="Qiziqdi")
    try:
        await harness.send("tur kerak")
        assert "Qiziqdi" in harness.fake.texts_to(GROUP_ID)[-1]
    finally:
        _detach_routers()
