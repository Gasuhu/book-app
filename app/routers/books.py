from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Book
from ..schemas import BookIn, BookOut

router = APIRouter(prefix="/books", tags=["books"])
DB = Annotated[Session, Depends(get_db)]


def _get_book(db: Session, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found.")
    return book


def _ensure_isbn_free(db: Session, isbn: str | None, exclude_id: int | None = None) -> None:
    if isbn is None:
        return
    stmt = select(Book.id).where(Book.isbn == isbn)
    if exclude_id is not None:
        stmt = stmt.where(Book.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"A book with ISBN {isbn} already exists.")


@router.get("", response_model=list[BookOut])
def list_books(
    db: DB,
    q: str | None = None,
    genre: str | None = None,
    available: bool | None = None,
):
    """List books. Search by title, author or ISBN with `q`."""
    stmt = select(Book)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Book.title.ilike(like), Book.author.ilike(like), Book.isbn.ilike(like)))
    if genre:
        stmt = stmt.where(Book.genre == genre)
    if available is True:
        stmt = stmt.where(Book.copies > Book.active_rentals)
    elif available is False:
        stmt = stmt.where(Book.copies <= Book.active_rentals)
    return db.scalars(stmt.order_by(Book.title)).all()


@router.get("/genres", response_model=list[str])
def list_genres(db: DB):
    stmt = select(Book.genre).where(Book.genre.is_not(None)).distinct().order_by(Book.genre)
    return db.scalars(stmt).all()


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: DB):
    return _get_book(db, book_id)


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(payload: BookIn, db: DB):
    _ensure_isbn_free(db, payload.isbn)
    book = Book(**payload.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.put("/{book_id}", response_model=BookOut)
def update_book(book_id: int, payload: BookIn, db: DB):
    book = _get_book(db, book_id)
    _ensure_isbn_free(db, payload.isbn, exclude_id=book_id)
    if payload.copies < book.active_rentals:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{book.active_rentals} copies are on loan, so there must be at least that many copies.",
        )
    for field, value in payload.model_dump().items():
        setattr(book, field, value)
    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, db: DB):
    book = _get_book(db, book_id)
    if book.active_rentals:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This book is still on loan. Return all copies before deleting it."
        )
    db.delete(book)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
