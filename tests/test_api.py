from datetime import timedelta

from app.database import utcnow
from app.models import Rental
from app.seed import seed_if_empty


def rent(client, user, book, **extra):
    return client.post("/api/rentals", json={"user_id": user["id"], "book_id": book["id"], **extra})


# ---------- Books ----------


def test_create_and_list_books(client, make_book):
    make_book(title="The Hobbit", author="J.R.R. Tolkien", genre="Fantasy", copies=2)
    make_book(title="Dune", author="Frank Herbert", genre="Science Fiction")

    books = client.get("/api/books").json()
    assert [b["title"] for b in books] == ["Dune", "The Hobbit"]
    assert books[1]["available_copies"] == 2

    assert [b["title"] for b in client.get("/api/books", params={"q": "tolk"}).json()] == ["The Hobbit"]
    assert [b["title"] for b in client.get("/api/books", params={"genre": "Fantasy"}).json()] == ["The Hobbit"]
    assert client.get("/api/books/genres").json() == ["Fantasy", "Science Fiction"]


def test_book_validation(client, make_book):
    assert client.post("/api/books", json={"title": "  ", "author": "X"}).status_code == 422
    assert client.post("/api/books", json={"title": "X", "author": "Y", "copies": 0}).status_code == 422
    assert client.post("/api/books", json={"title": "X", "author": "Y", "isbn": "123"}).status_code == 422

    book = make_book(isbn="978-0-441-17271-9", genre="", shelf="  ")
    assert book["isbn"] == "9780441172719"
    assert book["genre"] is None and book["shelf"] is None

    duplicate = client.post("/api/books", json={"title": "Copy", "author": "Y", "isbn": "9780441172719"})
    assert duplicate.status_code == 409


def test_update_and_delete_book(client, make_book):
    book = make_book()
    response = client.put(f"/api/books/{book['id']}", json={"title": "Dune Messiah", "author": "Frank Herbert", "copies": 3})
    assert response.status_code == 200
    assert response.json()["title"] == "Dune Messiah"
    assert response.json()["available_copies"] == 3

    assert client.delete(f"/api/books/{book['id']}").status_code == 204
    assert client.get(f"/api/books/{book['id']}").status_code == 404


# ---------- Members ----------


def test_member_crud_and_unique_email(client, make_user):
    user = make_user(name="Amina", email="Amina@Example.com")
    assert user["email"] == "amina@example.com"
    assert user["active_rentals"] == 0

    assert client.post("/api/users", json={"name": "Other", "email": "amina@example.com"}).status_code == 409
    assert client.post("/api/users", json={"name": "Bad", "email": "not-an-email"}).status_code == 422

    updated = client.put(f"/api/users/{user['id']}", json={"name": "Amina B.", "email": "amina@example.com"})
    assert updated.status_code == 200 and updated.json()["name"] == "Amina B."

    assert [u["name"] for u in client.get("/api/users", params={"q": "amina"}).json()] == ["Amina B."]
    assert client.delete(f"/api/users/{user['id']}").status_code == 204


# ---------- Rentals ----------


def test_rent_and_return_updates_availability(client, make_book, make_user):
    book = make_book(copies=2)
    user = make_user()

    response = rent(client, user, book, days=7)
    assert response.status_code == 201
    rental = response.json()
    assert rental["status"] == "active"
    assert rental["book"]["title"] == "Dune"
    assert rental["user"]["name"] == user["name"]

    assert client.get(f"/api/books/{book['id']}").json()["available_copies"] == 1
    assert client.get(f"/api/users/{user['id']}").json()["active_rentals"] == 1

    returned = client.post(f"/api/rentals/{rental['id']}/return")
    assert returned.status_code == 200
    assert returned.json()["status"] == "returned"
    assert client.get(f"/api/books/{book['id']}").json()["available_copies"] == 2

    # Can't return the same rental twice.
    assert client.post(f"/api/rentals/{rental['id']}/return").status_code == 409


def test_cannot_rent_when_no_copies_left(client, make_book, make_user):
    book = make_book(copies=1)
    first, second = make_user(), make_user()

    assert rent(client, first, book).status_code == 201
    response = rent(client, second, book)
    assert response.status_code == 409
    assert "No copies" in response.json()["detail"]

    assert [b["id"] for b in client.get("/api/books", params={"available": "false"}).json()] == [book["id"]]
    assert client.get("/api/books", params={"available": "true"}).json() == []


def test_member_cannot_hold_two_copies_of_same_book(client, make_book, make_user):
    book = make_book(copies=3)
    user = make_user()
    assert rent(client, user, book).status_code == 201
    assert rent(client, user, book).status_code == 409


def test_max_active_rentals_per_member(client, make_book, make_user):
    user = make_user()
    for i in range(3):  # MAX_ACTIVE_RENTALS=3 in conftest
        assert rent(client, user, make_book(title=f"Book {i}")).status_code == 201
    response = rent(client, user, make_book(title="One too many"))
    assert response.status_code == 409
    assert "maximum" in response.json()["detail"]


def test_rent_unknown_user_or_book(client, make_book, make_user):
    book, user = make_book(), make_user()
    assert client.post("/api/rentals", json={"user_id": 999, "book_id": book["id"]}).status_code == 404
    assert client.post("/api/rentals", json={"user_id": user["id"], "book_id": 999}).status_code == 404
    assert rent(client, user, book, days=0).status_code == 422
    assert rent(client, user, book, days=365).status_code == 422


def test_overdue_status_and_filters(client, db, make_book, make_user):
    user = make_user()
    late = rent(client, user, make_book(title="Late book")).json()
    rent(client, user, make_book(title="On time book"))

    rental = db.get(Rental, late["id"])
    rental.rented_at = utcnow() - timedelta(days=20)
    rental.due_at = utcnow() - timedelta(days=6)
    db.commit()

    assert client.get(f"/api/rentals/{late['id']}").json()["status"] == "overdue"
    assert [r["book"]["title"] for r in client.get("/api/rentals", params={"status": "overdue"}).json()] == ["Late book"]
    assert [r["book"]["title"] for r in client.get("/api/rentals", params={"status": "active"}).json()] == ["On time book"]
    assert len(client.get("/api/rentals", params={"status": "on_loan"}).json()) == 2
    assert client.get("/api/rentals", params={"status": "returned"}).json() == []
    assert client.get("/api/rentals", params={"status": "nope"}).status_code == 422

    stats = client.get("/api/stats").json()
    assert stats == {"titles": 2, "copies": 2, "available": 0, "members": 1, "on_loan": 2, "overdue": 1}


def test_cannot_delete_while_on_loan(client, make_book, make_user):
    book, user = make_book(copies=2), make_user()
    rental = rent(client, user, book).json()

    assert client.delete(f"/api/books/{book['id']}").status_code == 409
    assert client.delete(f"/api/users/{user['id']}").status_code == 409
    # Can't drop the number of copies below what is currently lent out.
    too_few = client.put(f"/api/books/{book['id']}", json={"title": "Dune", "author": "Frank Herbert", "copies": 0})
    assert too_few.status_code == 422

    client.post(f"/api/rentals/{rental['id']}/return")
    assert client.delete(f"/api/users/{user['id']}").status_code == 204
    # The member's rental history is removed with them.
    assert client.get("/api/rentals").json() == []
    assert client.delete(f"/api/books/{book['id']}").status_code == 204


def test_reducing_copies_below_loans_is_rejected(client, make_book, make_user):
    book = make_book(copies=3)
    rent(client, make_user(), book)
    rent(client, make_user(), book)
    response = client.put(f"/api/books/{book['id']}", json={"title": "Dune", "author": "Frank Herbert", "copies": 1})
    assert response.status_code == 409


# ---------- Misc ----------


def test_seed_only_runs_on_empty_database(client, db):
    assert seed_if_empty(db) is True
    assert seed_if_empty(db) is False
    stats = client.get("/api/stats").json()
    assert stats["titles"] == 12
    assert stats["members"] == 5
    assert stats["overdue"] == 2


def test_frontend_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Libris" in response.text
    assert client.get("/api/health").json() == {"status": "ok"}
