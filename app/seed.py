"""Sample data so the app isn't empty on first launch.

Runs automatically on startup when the database has no books
(disable with SEED_DEMO_DATA=0), or manually with:  python -m app.seed
"""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, utcnow
from .models import Book, Rental, User

BOOKS = [
    dict(title="Pride and Prejudice", author="Jane Austen", genre="Classic", published_year=1813,
         pages=432, copies=3, shelf="A1",
         description="Elizabeth Bennet trades wit with the proud Mr. Darcy in a sharp comedy of manners."),
    dict(title="1984", author="George Orwell", genre="Dystopian", published_year=1949, pages=328,
         copies=2, shelf="B2",
         description="Winston Smith quietly rebels against a regime that watches, rewrites and controls everything."),
    dict(title="To Kill a Mockingbird", author="Harper Lee", genre="Classic", published_year=1960,
         pages=281, copies=2, shelf="A1",
         description="Scout Finch watches her father defend a Black man falsely accused in 1930s Alabama."),
    dict(title="The Hobbit", author="J.R.R. Tolkien", genre="Fantasy", published_year=1937, pages=310,
         copies=2, shelf="C1",
         description="Bilbo Baggins is swept from his comfortable hole into a quest for a dragon's treasure."),
    dict(title="Dune", author="Frank Herbert", genre="Science Fiction", published_year=1965, pages=412,
         copies=1, shelf="C3",
         description="On the desert planet Arrakis, Paul Atreides is caught in a war over the universe's most precious resource."),
    dict(title="The Great Gatsby", author="F. Scott Fitzgerald", genre="Classic", published_year=1925,
         pages=180, copies=1, shelf="A2",
         description="Nick Carraway is drawn into the glittering, hollow world of his mysterious neighbour Jay Gatsby."),
    dict(title="One Hundred Years of Solitude", author="Gabriel García Márquez", genre="Magical Realism",
         published_year=1967, pages=417, copies=1, shelf="A3",
         description="Seven generations of the Buendía family rise and fall in the town of Macondo."),
    dict(title="Brave New World", author="Aldous Huxley", genre="Dystopian", published_year=1932,
         pages=311, copies=1, shelf="B2",
         description="A future society engineered for comfort and stability, at the cost of everything human."),
    dict(title="Frankenstein", author="Mary Shelley", genre="Horror", published_year=1818, pages=280,
         copies=1, shelf="B1",
         description="Victor Frankenstein creates life, and then flees from what he has made."),
    dict(title="The Little Prince", author="Antoine de Saint-Exupéry", genre="Fable", published_year=1943,
         pages=96, copies=2, shelf="D1",
         description="A pilot stranded in the desert meets a small prince who has travelled from a tiny asteroid."),
    dict(title="The Alchemist", author="Paulo Coelho", genre="Fiction", published_year=1988, pages=208,
         copies=2, shelf="A4",
         description="Santiago, a shepherd boy, follows a recurring dream across the desert toward his treasure."),
    dict(title="Foundation", author="Isaac Asimov", genre="Science Fiction", published_year=1951,
         pages=255, copies=1, shelf="C3",
         description="Mathematician Hari Seldon plans to shorten the dark age that follows a galactic empire's fall."),
]

USERS = [
    dict(name="Amina Benali", email="amina.benali@example.com", phone="+1 555 0101"),
    dict(name="Lucas Martin", email="lucas.martin@example.com", phone="+1 555 0102"),
    dict(name="Sofia Rossi", email="sofia.rossi@example.com"),
    dict(name="Yuki Tanaka", email="yuki.tanaka@example.com", phone="+1 555 0104"),
    dict(name="Omar Haddad", email="omar.haddad@example.com"),
]

# (user index, book index, rented days ago, loan length in days, returned days ago or None)
RENTALS = [
    (0, 1, 3, 14, None),
    (0, 3, 10, 14, None),
    (1, 4, 20, 14, None),   # overdue
    (2, 0, 5, 21, None),
    (3, 9, 12, 14, None),
    (4, 6, 18, 14, None),   # overdue
    (1, 5, 40, 14, 30),     # returned
    (2, 10, 25, 14, 15),    # returned
]


def seed_if_empty(db: Session) -> bool:
    """Insert sample data if there are no books yet. Returns True if it seeded."""
    if db.scalar(select(func.count(Book.id))):
        return False

    books = [Book(**data) for data in BOOKS]
    users = [User(**data) for data in USERS]
    db.add_all(books + users)

    now = utcnow()
    for user_idx, book_idx, rented_ago, loan_days, returned_ago in RENTALS:
        rented_at = now - timedelta(days=rented_ago)
        db.add(
            Rental(
                user=users[user_idx],
                book=books[book_idx],
                rented_at=rented_at,
                due_at=rented_at + timedelta(days=loan_days),
                returned_at=None if returned_ago is None else now - timedelta(days=returned_ago),
            )
        )
    db.commit()
    return True


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        print("Sample data added." if seed_if_empty(session) else "Database already has books; nothing to do.")
