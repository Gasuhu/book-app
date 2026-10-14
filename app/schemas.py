import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from .config import settings


def _blank_to_none(value):
    if isinstance(value, str) and not value.strip():
        return None
    return value


# Optional text field where an empty string from a form means "not set".
OptionalStr = Annotated[str | None, BeforeValidator(_blank_to_none)]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ISBN_RE = re.compile(r"^(\d{9}[\dX]|\d{13})$")

RentalStatus = Literal["active", "overdue", "returned"]


# ---------- Books ----------


class BookIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    genre: OptionalStr = Field(default=None, max_length=80)
    published_year: int | None = Field(default=None, ge=0, le=2100)
    pages: int | None = Field(default=None, ge=1, le=50000)
    copies: int = Field(default=1, ge=1, le=999)
    shelf: OptionalStr = Field(default=None, max_length=40)
    isbn: OptionalStr = Field(default=None, max_length=20)
    description: OptionalStr = Field(default=None, max_length=4000)

    @field_validator("isbn")
    @classmethod
    def normalize_isbn(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.replace("-", "").replace(" ", "").upper()
        if not ISBN_RE.match(value):
            raise ValueError("must be a 10 or 13 digit ISBN")
        return value


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    genre: str | None
    published_year: int | None
    pages: int | None
    copies: int
    available_copies: int
    shelf: str | None
    isbn: str | None
    description: str | None
    created_at: datetime


class BookBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str


# ---------- Users ----------


class UserIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=255)
    phone: OptionalStr = Field(default=None, max_length=40)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.lower()
        if not EMAIL_RE.match(value):
            raise ValueError("must be a valid email address")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str | None
    active_rentals: int
    created_at: datetime


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


# ---------- Rentals ----------


class RentalCreate(BaseModel):
    user_id: int
    book_id: int
    days: int = Field(default=settings.default_loan_days, ge=1, le=settings.max_loan_days)


class RentalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    book_id: int
    rented_at: datetime
    due_at: datetime
    returned_at: datetime | None
    status: RentalStatus
    user: UserBrief
    book: BookBrief


# ---------- Stats ----------


class Stats(BaseModel):
    titles: int
    copies: int
    available: int
    members: int
    on_loan: int
    overdue: int
