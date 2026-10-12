from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session

from flashcards.db import get_session, init_db, make_engine
from flashcards.deps import get_now, get_today
from flashcards.main import app
from flashcards.models import Card

# Festes "Heute" für alle Tests, die über die App laufen.
TODAY = date(2026, 3, 10)


class Clock:
    """Stellbare Uhr, damit Lernsitzungen in Tests eindeutige Zeitpunkte haben."""

    def __init__(self):
        self.now = datetime(2026, 3, 10, 9, 0, tzinfo=UTC)

    def tick(self, minutes: int = 1) -> datetime:
        self.now += timedelta(minutes=minutes)
        return self.now


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


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def client(engine, clock):
    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_today] = lambda: TODAY
    app.dependency_overrides[get_now] = lambda: clock.now
    # Ohne "with": der Lifespan läuft nicht, es entsteht keine echte DB-Datei.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def deck(client):
    return client.post("/api/decks", json={"name": "Spanisch"}).json()


@pytest.fixture
def add_card(client, engine, deck):
    """Legt eine Karte an und setzt bei Bedarf Fach und Fälligkeit direkt in der DB."""

    def _add(front, back="x", box=1, due_in_days=0, deck_id=None):
        card = client.post(
            f"/api/decks/{deck_id or deck['id']}/cards", json={"front": front, "back": back}
        ).json()
        with Session(engine) as session:
            stored = session.get(Card, card["id"])
            stored.box = box
            stored.due_date = TODAY + timedelta(days=due_in_days)
            session.add(stored)
            session.commit()
        return card["id"]

    return _add
