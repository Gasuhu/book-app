from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db, utcnow
from ..models import Book, Rental, User
from ..schemas import Stats

router = APIRouter(tags=["stats"])
DB = Annotated[Session, Depends(get_db)]


@router.get("/stats", response_model=Stats)
def get_stats(db: DB):
    """Numbers for the dashboard."""
    titles = db.scalar(select(func.count(Book.id))) or 0
    copies = db.scalar(select(func.coalesce(func.sum(Book.copies), 0))) or 0
    members = db.scalar(select(func.count(User.id))) or 0
    on_loan = db.scalar(select(func.count(Rental.id)).where(Rental.returned_at.is_(None))) or 0
    overdue = (
        db.scalar(
            select(func.count(Rental.id)).where(Rental.returned_at.is_(None), Rental.due_at < utcnow())
        )
        or 0
    )
    return Stats(
        titles=titles,
        copies=copies,
        available=max(copies - on_loan, 0),
        members=members,
        on_loan=on_loan,
        overdue=overdue,
    )
