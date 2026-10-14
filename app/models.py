from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from .database import Base, UTCDateTime, utcnow


class Rental(Base):
    __tablename__ = "rentals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    rented_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    due_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    returned_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)

    user: Mapped["User"] = relationship(back_populates="rentals")
    book: Mapped["Book"] = relationship(back_populates="rentals")

    @property
    def status(self) -> str:
        if self.returned_at is not None:
            return "returned"
        if self.due_at < utcnow():
            return "overdue"
        return "active"


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    author: Mapped[str] = mapped_column(String(255), index=True)
    genre: Mapped[str | None] = mapped_column(String(80), index=True)
    published_year: Mapped[int | None] = mapped_column(Integer)
    pages: Mapped[int | None] = mapped_column(Integer)
    copies: Mapped[int] = mapped_column(Integer, default=1)
    shelf: Mapped[str | None] = mapped_column(String(40))
    isbn: Mapped[str | None] = mapped_column(String(20), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    rentals: Mapped[list[Rental]] = relationship(
        back_populates="book", cascade="all, delete-orphan", passive_deletes=True
    )

    # Number of copies currently out on loan, computed in SQL with every query.
    active_rentals: Mapped[int] = column_property(
        select(func.count(Rental.id))
        .where(Rental.book_id == id, Rental.returned_at.is_(None))
        .correlate_except(Rental)
        .scalar_subquery()
    )

    @property
    def available_copies(self) -> int:
        return max(self.copies - (self.active_rentals or 0), 0)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    rentals: Mapped[list[Rental]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    active_rentals: Mapped[int] = column_property(
        select(func.count(Rental.id))
        .where(Rental.user_id == id, Rental.returned_at.is_(None))
        .correlate_except(Rental)
        .scalar_subquery()
    )
