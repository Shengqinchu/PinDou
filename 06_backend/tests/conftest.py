from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from pindou.db.models import Base

os.environ.setdefault("DATABASE_URL", "sqlite:///./var/test.db")
os.environ.setdefault("ENABLE_REVERSE_PROXY_HEALTH_MONITOR", "false")
os.environ.setdefault("ENABLE_EXPIRED_ORIGINAL_DELETE_TASK", "false")


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionTesting = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with SessionTesting() as session:
        yield session
    Base.metadata.drop_all(engine)
