"""SQLAlchemy engine + session. Switch databases by changing DATABASE_URL."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# check_same_thread=False: scrapes save results from background threads
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create tables and the two store rows (safe to call on every start)."""
    from app import models  # noqa: F401 - registers the tables on Base

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for name, url in models.STORES.items():
            if not db.query(models.Store).filter_by(name=name).first():
                db.add(models.Store(name=name, base_url=url))
        db.commit()


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    with SessionLocal() as db:
        yield db
