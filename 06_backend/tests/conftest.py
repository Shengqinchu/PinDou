from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from pindou.db.models import Base
from pindou.services.cdk_service import CDKService


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


@pytest.fixture(autouse=True)
def reset_cdk_attempts() -> None:
    CDKService._attempts = []
    yield
    CDKService._attempts = []
