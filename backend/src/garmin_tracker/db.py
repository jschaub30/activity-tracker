from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from garmin_tracker.config import get_settings

# Import models so SQLModel metadata is populated before create_all
from garmin_tracker import models as _models  # noqa: F401

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=settings.debug, connect_args=connect_args)


def init_db() -> None:
    # Ensure SQLite parent directory exists
    if settings.database_url.startswith("sqlite:///"):
        raw = settings.database_url.replace("sqlite:///", "", 1)
        db_path = Path(raw)
        if not db_path.is_absolute():
            # Relative paths are resolved from backend/ (cwd when running uv)
            db_path = Path.cwd() / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
