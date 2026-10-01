import enum
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(64))
    lang: Mapped[str] = mapped_column(String(2), default="uz")
    phone: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TourCategory(str, enum.Enum):
    DOMESTIC = "domestic"  # O'zbekiston bo'ylab
    ABROAD = "abroad"  # xorijga
    PILGRIMAGE = "pilgrimage"  # umra / haj


class Tour(Base):
    __tablename__ = "tours"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[TourCategory] = mapped_column(
        Enum(TourCategory, values_callable=lambda e: [m.value for m in e]),
        default=TourCategory.DOMESTIC,
    )
    # uz is the main text; ru/en are optional translations (filled by admin or AI)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    title_ru: Mapped[str | None] = mapped_column(String(255))
    description_ru: Mapped[str | None] = mapped_column(Text)
    title_en: Mapped[str | None] = mapped_column(String(255))
    description_en: Mapped[str | None] = mapped_column(Text)
    price: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    start_date: Mapped[date | None] = mapped_column(Date)
    seats: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    def title_for(self, lang: str) -> str:
        return getattr(self, f"title_{lang}", None) or self.title

    def description_for(self, lang: str) -> str:
        return getattr(self, f"description_{lang}", None) or self.description


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    people: Mapped[int] = mapped_column(Integer)
    phone: Mapped[str] = mapped_column(String(32))
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, values_callable=lambda e: [m.value for m in e]),
        default=BookingStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(lazy="joined")
    tour: Mapped[Tour] = relationship(lazy="joined")


class Lead(Base):
    """A potential customer the admin should contact (from the AI chat)."""

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    phone: Mapped[str | None] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(lazy="joined")


class ChatMessage(Base):
    """AI assistant conversation history, per user."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
