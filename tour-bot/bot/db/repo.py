from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import AppSetting, Booking, BookingStatus, ChatMessage, Lead, Tour, TourCategory, User


async def get_or_create_user(session: AsyncSession, tg_id: int, full_name: str, username: str | None) -> User:
    user = await session.scalar(select(User).where(User.tg_id == tg_id))
    if user is None:
        user = User(tg_id=tg_id, full_name=full_name, username=username)
        session.add(user)
        await session.commit()
    return user


async def set_user_lang(session: AsyncSession, tg_id: int, lang: str) -> None:
    user = await session.scalar(select(User).where(User.tg_id == tg_id))
    if user is not None:
        user.lang = lang
        await session.commit()


async def list_active_tours(session: AsyncSession, category: TourCategory | None = None) -> list[Tour]:
    query = select(Tour).where(Tour.is_active.is_(True))
    if category is not None:
        query = query.where(Tour.category == category)
    result = await session.scalars(query.order_by(Tour.start_date, Tour.id))
    return list(result)


async def get_tour(session: AsyncSession, tour_id: int) -> Tour | None:
    return await session.get(Tour, tour_id)


async def add_tour(
    session: AsyncSession,
    title: str,
    description: str,
    price: int,
    seats: int,
    start_date: date | None = None,
    currency: str = "USD",
    category: TourCategory = TourCategory.DOMESTIC,
    **translations: str | None,
) -> Tour:
    tour = Tour(
        title=title,
        description=description,
        price=price,
        seats=seats,
        start_date=start_date,
        currency=currency,
        category=category,
        **translations,
    )
    session.add(tour)
    await session.commit()
    return tour


async def free_seats(session: AsyncSession, tour: Tour) -> int:
    """Seats left after pending and confirmed bookings."""
    taken = await session.scalar(
        select(func.coalesce(func.sum(Booking.people), 0)).where(
            Booking.tour_id == tour.id, Booking.status != BookingStatus.REJECTED
        )
    )
    return tour.seats - int(taken or 0)


async def create_booking(session: AsyncSession, user: User, tour: Tour, people: int, phone: str) -> Booking:
    user.phone = phone
    booking = Booking(user_id=user.id, tour_id=tour.id, people=people, phone=phone)
    session.add(booking)
    await session.commit()
    return await get_booking(session, booking.id)


async def get_booking(session: AsyncSession, booking_id: int) -> Booking | None:
    return await session.get(Booking, booking_id)


async def set_booking_status(session: AsyncSession, booking_id: int, status: BookingStatus) -> Booking | None:
    booking = await get_booking(session, booking_id)
    if booking is None or booking.status != BookingStatus.PENDING:
        return None
    booking.status = status
    await session.commit()
    return booking


async def user_bookings(session: AsyncSession, tg_id: int) -> list[Booking]:
    result = await session.scalars(
        select(Booking).join(Booking.user).where(User.tg_id == tg_id).order_by(Booking.created_at.desc(), Booking.id.desc())
    )
    return list(result.unique())


async def chat_history(session: AsyncSession, user: User, limit: int = 20) -> list[ChatMessage]:
    result = await session.scalars(
        select(ChatMessage).where(ChatMessage.user_id == user.id).order_by(ChatMessage.id.desc()).limit(limit)
    )
    return list(reversed(list(result)))


async def add_chat_messages(session: AsyncSession, user: User, *pairs: tuple[str, str]) -> None:
    session.add_all(ChatMessage(user_id=user.id, role=role, content=content) for role, content in pairs)
    await session.commit()


async def recent_lead_exists(session: AsyncSession, user: User, within: timedelta = timedelta(hours=6)) -> bool:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - within  # SQLite now() is naive UTC
    lead_id = await session.scalar(select(Lead.id).where(Lead.user_id == user.id, Lead.created_at >= since).limit(1))
    return lead_id is not None


async def create_lead(session: AsyncSession, user: User, summary: str, phone: str | None) -> Lead:
    if phone:
        user.phone = phone
    lead = Lead(user_id=user.id, summary=summary, phone=phone or user.phone)
    session.add(lead)
    await session.commit()
    return await session.get(Lead, lead.id)


async def get_setting(session: AsyncSession, key: str) -> str | None:
    row = await session.get(AppSetting, key)
    return row.value if row else None


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    row = await session.get(AppSetting, key)
    if row is None:
        session.add(AppSetting(key=key, value=value))
    else:
        row.value = value
    await session.commit()
