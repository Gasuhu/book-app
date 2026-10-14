"""Application settings, read from environment variables."""

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


@dataclass(frozen=True)
class Settings:
    # SQLite by default. For Postgres use e.g.
    #   postgresql+psycopg://user:password@localhost:5432/library
    database_url: str
    # Echo SQL statements to the log (handy while developing).
    sql_echo: bool
    # Fill an empty database with sample books, members and rentals on startup.
    seed_demo_data: bool
    default_loan_days: int
    max_loan_days: int
    max_active_rentals: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./library.db"),
            sql_echo=_env_bool("SQL_ECHO", False),
            seed_demo_data=_env_bool("SEED_DEMO_DATA", True),
            default_loan_days=_env_int("DEFAULT_LOAN_DAYS", 14),
            max_loan_days=_env_int("MAX_LOAN_DAYS", 90),
            max_active_rentals=_env_int("MAX_ACTIVE_RENTALS", 5),
        )


settings = Settings.from_env()
