from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import UserIn, UserOut

router = APIRouter(prefix="/users", tags=["users"])
DB = Annotated[Session, Depends(get_db)]


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found.")
    return user


def _ensure_email_free(db: Session, email: str, exclude_id: int | None = None) -> None:
    stmt = select(User.id).where(User.email == email)
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"A member with email {email} already exists.")


@router.get("", response_model=list[UserOut])
def list_users(db: DB, q: str | None = None):
    """List members. Search by name or email with `q`."""
    stmt = select(User)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like)))
    return db.scalars(stmt.order_by(User.name)).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: DB):
    return _get_user(db, user_id)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserIn, db: DB):
    _ensure_email_free(db, payload.email)
    user = User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserIn, db: DB):
    user = _get_user(db, user_id)
    _ensure_email_free(db, payload.email, exclude_id=user_id)
    for field, value in payload.model_dump().items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: DB):
    user = _get_user(db, user_id)
    if user.active_rentals:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"{user.name} still has books on loan. Return them before deleting."
        )
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
