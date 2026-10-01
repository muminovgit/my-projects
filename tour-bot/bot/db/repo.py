from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Booking, BookingStatus, Tour, User


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


async def list_active_tours(session: AsyncSession) -> list[Tour]:
    result = await session.scalars(select(Tour).where(Tour.is_active.is_(True)).order_by(Tour.start_date, Tour.id))
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
) -> Tour:
    tour = Tour(title=title, description=description, price=price, seats=seats, start_date=start_date, currency=currency)
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
