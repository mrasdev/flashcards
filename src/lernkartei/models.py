from datetime import UTC, date, datetime

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    # SQLModel speichert Zeitstempel nur mit Zeitzone, intern immer als UTC.
    return datetime.now(UTC)


class Deck(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=utc_now)

    cards: list["Card"] = Relationship(back_populates="deck", cascade_delete=True)


class Card(SQLModel, table=True):
    __table_args__ = (CheckConstraint("box BETWEEN 1 AND 5", name="ck_card_box_range"),)

    id: int | None = Field(default=None, primary_key=True)
    deck_id: int = Field(foreign_key="deck.id", ondelete="CASCADE", index=True)
    front: str
    back: str
    # Neue Karten starten in Fach 1 und sind sofort fällig.
    box: int = Field(default=1)
    due_date: date = Field(default_factory=date.today)
    last_reviewed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)

    deck: Deck = Relationship(back_populates="cards")
