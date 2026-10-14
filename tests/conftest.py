import os
import tempfile

# Point the app at a throwaway database before it is imported.
_tmpdir = tempfile.mkdtemp(prefix="libris-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["SEED_DEMO_DATA"] = "0"
os.environ["MAX_ACTIVE_RENTALS"] = "3"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def make_book(client):
    def _make(**overrides):
        data = {"title": "Dune", "author": "Frank Herbert", "copies": 1, **overrides}
        response = client.post("/api/books", json=data)
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture
def make_user(client):
    counter = iter(range(1, 1000))

    def _make(**overrides):
        n = next(counter)
        data = {"name": f"Reader {n}", "email": f"reader{n}@example.com", **overrides}
        response = client.post("/api/users", json=data)
        assert response.status_code == 201, response.text
        return response.json()

    return _make
