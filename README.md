# Libris — Library Management

A small library management system: keep track of the **books** on your shelves, your **members**, and who has **rented** what.

- **Backend:** Python + [FastAPI](https://fastapi.tiangolo.com/)
- **Database:** SQLite by default, via [SQLAlchemy 2.0](https://docs.sqlalchemy.org/) (switch to PostgreSQL by changing one environment variable)
- **Frontend:** a single `index.html` file (no build step, no framework) with a teal theme, dark mode and a mobile layout

## Features

- **Bookshelf**: add, edit and delete books (title, author, genre, year, pages, shelf location, ISBN, description, number of copies). You can search, filter by genre, and filter by availability.
- **Members**: add, edit and delete members, and see each member's current loans and history.
- **Rentals**: lend a book to a member for a number of days, then mark it returned. Overdue books are flagged automatically.
- **Overview** dashboard: stats, overdue books, what's due soon, and recently added books.
- Rules the API enforces:
  - A book can't be lent out when no copies are left.
  - A member can't borrow two copies of the same book.
  - A member can hold at most 5 books at once (configurable).
  - A book or member can't be deleted while books are still on loan.
  - A book's number of copies can't be lowered below the number currently on loan.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

Then open:

- **App:** http://localhost:8000
- **Interactive API docs:** http://localhost:8000/docs

On first start the database (`library.db`) is created and filled with sample books, members and rentals so there's something to look at. Set `SEED_DEMO_DATA=0` to start empty.

## Using PostgreSQL

All database access goes through SQLAlchemy, so only the connection URL changes:

```bash
pip install "psycopg[binary]"
export DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/library"
uvicorn app.main:app
```

Tables are created automatically on startup. When renting a book, the book's row is locked (`SELECT … FOR UPDATE`) so two people can't grab the last copy at the same time on Postgres.

## Configuration

All settings are environment variables:

| Variable              | Default                   | Description                                         |
| --------------------- | ------------------------- | --------------------------------------------------- |
| `DATABASE_URL`        | `sqlite:///./library.db`  | Any SQLAlchemy database URL                         |
| `SEED_DEMO_DATA`      | `1`                       | Add sample data when the database has no books      |
| `DEFAULT_LOAN_DAYS`   | `14`                      | Loan period when none is given                      |
| `MAX_LOAN_DAYS`       | `90`                      | Longest allowed loan period                         |
| `MAX_ACTIVE_RENTALS`  | `5`                       | How many books one member can have at once          |
| `SQL_ECHO`            | `0`                       | Log every SQL statement                             |

## API overview

| Method   | Path                          | What it does                                                  |
| -------- | ----------------------------- | ------------------------------------------------------------- |
| `GET`    | `/api/books`                  | List books (`?q=`, `?genre=`, `?available=true/false`)        |
| `POST`   | `/api/books`                  | Add a book                                                    |
| `GET`    | `/api/books/genres`           | All genres in use                                             |
| `GET`    | `/api/books/{id}`             | Get a book                                                    |
| `PUT`    | `/api/books/{id}`             | Update a book                                                 |
| `DELETE` | `/api/books/{id}`             | Delete a book                                                 |
| `GET`    | `/api/users`                  | List members (`?q=`)                                          |
| `POST`   | `/api/users`                  | Add a member                                                  |
| `GET`    | `/api/users/{id}`             | Get a member                                                  |
| `PUT`    | `/api/users/{id}`             | Update a member                                               |
| `DELETE` | `/api/users/{id}`             | Delete a member                                               |
| `GET`    | `/api/rentals`                | List rentals (`?status=on_loan/active/overdue/returned`, `?user_id=`, `?book_id=`) |
| `POST`   | `/api/rentals`                | Rent a book: `{"user_id": 1, "book_id": 2, "days": 14}`       |
| `POST`   | `/api/rentals/{id}/return`    | Mark a rental as returned                                     |
| `GET`    | `/api/stats`                  | Dashboard numbers                                             |

Full request/response schemas are at `/docs`.

## Project layout

```
app/
  main.py          FastAPI app, startup, serves the UI
  config.py        Settings from environment variables
  database.py      Engine, session and UTC datetime type (SQLite/Postgres agnostic)
  models.py        SQLAlchemy models: Book, User, Rental
  schemas.py       Pydantic request/response models and validation
  seed.py          Sample data (also runnable: python -m app.seed)
  routers/         books, users, rentals, stats endpoints
  static/index.html  The whole frontend in one file
tests/             pytest suite for the API
```

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Going further

- **Schema changes:** `create_all` only creates missing tables. Once you have real data, add [Alembic](https://alembic.sqlalchemy.org/) to migrate existing tables.
- **Authentication:** the API is open. Put it behind a login (e.g. FastAPI's OAuth2 utilities) before exposing it to the internet.
