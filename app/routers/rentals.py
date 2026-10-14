from datetime import timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..database import get_db, utcnow
from ..models import Book, Rental, User
from ..schemas import RentalCreate, RentalOut

router = APIRouter(prefix="/rentals", tags=["rentals"])
DB = Annotated[Session, Depends(get_db)]

# on_loan = not yet returned (active + overdue)
StatusFilter = Literal["on_loan", "active", "overdue", "returned"]


def _get_rental(db: Session, rental_id: int) -> Rental:
    rental = db.get(Rental, rental_id, options=[joinedload(Rental.user), joinedload(Rental.book)])
    if rental is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rental not found.")
    return rental


def _count_open(db: Session, *criteria) -> int:
    stmt = select(func.count(Rental.id)).where(Rental.returned_at.is_(None), *criteria)
    return db.scalar(stmt) or 0


@router.get("", response_model=list[RentalOut])
def list_rentals(
    db: DB,
    status_filter: Annotated[StatusFilter | None, Query(alias="status")] = None,
    user_id: int | None = None,
    book_id: int | None = None,
):
    """List rentals, optionally filtered by status, member or book."""
    now = utcnow()
    stmt = select(Rental).options(joinedload(Rental.user), joinedload(Rental.book))

    if status_filter == "returned":
        stmt = stmt.where(Rental.returned_at.is_not(None)).order_by(Rental.returned_at.desc())
    elif status_filter in ("on_loan", "active", "overdue"):
        stmt = stmt.where(Rental.returned_at.is_(None)).order_by(Rental.due_at)
        if status_filter == "active":
            stmt = stmt.where(Rental.due_at >= now)
        elif status_filter == "overdue":
            stmt = stmt.where(Rental.due_at < now)
    else:
        stmt = stmt.order_by(Rental.rented_at.desc())

    if user_id is not None:
        stmt = stmt.where(Rental.user_id == user_id)
    if book_id is not None:
        stmt = stmt.where(Rental.book_id == book_id)
    return db.scalars(stmt).all()


@router.get("/{rental_id}", response_model=RentalOut)
def get_rental(rental_id: int, db: DB):
    return _get_rental(db, rental_id)


@router.post("", response_model=RentalOut, status_code=status.HTTP_201_CREATED)
def rent_book(payload: RentalCreate, db: DB):
    """Lend a copy of a book to a member."""
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found.")

    # Lock the book row (Postgres) so two people can't grab the last copy at once.
    book = db.get(Book, payload.book_id, with_for_update=True)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found.")

    if _count_open(db, Rental.book_id == book.id) >= book.copies:
        raise HTTPException(status.HTTP_409_CONFLICT, f"No copies of “{book.title}” are available right now.")

    if _count_open(db, Rental.book_id == book.id, Rental.user_id == user.id):
        raise HTTPException(status.HTTP_409_CONFLICT, f"{user.name} already has “{book.title}”.")

    if _count_open(db, Rental.user_id == user.id) >= settings.max_active_rentals:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{user.name} already has {settings.max_active_rentals} books, the maximum allowed.",
        )

    now = utcnow()
    rental = Rental(user=user, book=book, rented_at=now, due_at=now + timedelta(days=payload.days))
    db.add(rental)
    db.commit()
    return _get_rental(db, rental.id)


@router.post("/{rental_id}/return", response_model=RentalOut)
def return_book(rental_id: int, db: DB):
    """Mark a rental as returned."""
    rental = _get_rental(db, rental_id)
    if rental.returned_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This book has already been returned.")
    rental.returned_at = utcnow()
    db.commit()
    return _get_rental(db, rental.id)
