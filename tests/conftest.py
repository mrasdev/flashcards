import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session

from lernkartei.db import init_db, make_engine


@pytest.fixture
def engine():
    # StaticPool: alle Sessions teilen sich dieselbe In-Memory-Datenbank.
    engine = make_engine("sqlite://", poolclass=StaticPool)
    init_db(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session
