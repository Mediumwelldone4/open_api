from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .repositories import InMemoryConnectionRepository, SQLiteConnectionRepository


def create_repository(database_url: str) -> InMemoryConnectionRepository:
    """Instantiate a repository implementation based on the configured URL."""

    parsed = urlparse(database_url)

    if parsed.scheme in {"", "sqlite"}:
        # sqlite:///relative/path.db or sqlite:////absolute/path.db
        if database_url.endswith(":memory:"):
            return SQLiteConnectionRepository(":memory:")

        if database_url.startswith("sqlite:////"):
            db_path = Path("/" + database_url[len("sqlite:////"):])
        elif database_url.startswith("sqlite:///"):
            db_path = Path(database_url[len("sqlite:///"):])
        elif parsed.netloc:
            db_path = Path(f"/{parsed.netloc}{parsed.path}")
        elif parsed.path:
            db_path = Path(parsed.path)
        else:
            db_path = Path("data/open_data_insight.db")

        return SQLiteConnectionRepository(db_path)

    if parsed.scheme == "memory":
        return InMemoryConnectionRepository()

    raise ValueError(
        f"Unsupported database URL '{database_url}'. Provide a sqlite:/// path or memory://"
    )
