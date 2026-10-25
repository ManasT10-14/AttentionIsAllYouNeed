from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from odin.core.config import settings
from odin.db.tables import Base


@lru_cache
def engine():
    return create_engine(settings().database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)


@lru_cache
def _factory():
    return sessionmaker(bind=engine(), expire_on_commit=False)


@contextmanager
def db() -> Session:
    s = _factory()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def init_db() -> None:
    with engine().begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine())
    with engine().begin() as conn:   # ponytail: tiny additive migration; adopt Alembic when schema churns
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS gmail_address VARCHAR"))
