from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.exc import IntegrityError

from .config import settings
from .database import Base, SessionLocal, engine
from .routers import books, rentals, stats, users
from .seed import seed_if_empty

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Creates missing tables. For schema changes on an existing database, use Alembic.
    Base.metadata.create_all(bind=engine)
    if settings.seed_demo_data:
        with SessionLocal() as db:
            seed_if_empty(db)
    yield


app = FastAPI(
    title="Libris",
    description="A small library management API: books, members and rentals.",
    version="1.0.0",
    lifespan=lifespan,
)

for module in (books, users, rentals, stats):
    app.include_router(module.router, prefix="/api")


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_request: Request, _exc: IntegrityError):
    # Safety net for races the explicit checks can't see (e.g. two identical inserts at once).
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "This conflicts with existing data."},
    )


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
