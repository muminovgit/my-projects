from datetime import date

from bot.db.models import BookingStatus
from bot.db.repo import (
    add_tour,
    create_booking,
    free_seats,
    get_or_create_user,
    list_active_tours,
    set_booking_status,
    user_bookings,
)


async def test_get_or_create_user_is_idempotent(session):
    a = await get_or_create_user(session, 42, "Ali", "ali")
    b = await get_or_create_user(session, 42, "Ali", "ali")
    assert a.id == b.id
    assert a.lang == "uz"


async def test_list_active_tours_hides_inactive(session):
    await add_tour(session, "Samarqand", "", 100, 10, date(2026, 11, 1))
    hidden = await add_tour(session, "Eski", "", 50, 5)
    hidden.is_active = False
    await session.commit()
    assert [t.title for t in await list_active_tours(session)] == ["Samarqand"]


async def test_free_seats_ignores_rejected(session):
    user = await get_or_create_user(session, 1, "U", None)
    tour = await add_tour(session, "Buxoro", "", 80, 10)
    b1 = await create_booking(session, user, tour, 3, "+998901234567")
    b2 = await create_booking(session, user, tour, 4, "+998901234567")
    assert await free_seats(session, tour) == 3
    await set_booking_status(session, b2.id, BookingStatus.REJECTED)
    assert await free_seats(session, tour) == 7
    await set_booking_status(session, b1.id, BookingStatus.CONFIRMED)
    assert await free_seats(session, tour) == 7


async def test_booking_status_changes_only_once(session):
    user = await get_or_create_user(session, 1, "U", None)
    tour = await add_tour(session, "Xiva", "", 80, 10)
    booking = await create_booking(session, user, tour, 1, "+998901234567")
    assert await set_booking_status(session, booking.id, BookingStatus.CONFIRMED) is not None
    assert await set_booking_status(session, booking.id, BookingStatus.REJECTED) is None


async def test_user_bookings_and_phone_saved(session):
    user = await get_or_create_user(session, 7, "U", None)
    tour = await add_tour(session, "Xiva", "", 80, 10)
    await create_booking(session, user, tour, 2, "+998901112233")
    bookings = await user_bookings(session, 7)
    assert len(bookings) == 1 and bookings[0].tour.title == "Xiva"
    assert user.phone == "+998901112233"
