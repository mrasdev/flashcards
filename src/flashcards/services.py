"""Database operations shared by the JSON API and the HTML interface."""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, or_, select

from flashcards import leitner
from flashcards.models import Card, Deck


class EmptyTextError(ValueError):
    """A required text is empty or consists only of whitespace."""


class DuplicateDeckNameError(ValueError):
    """A deck with this name already exists."""


class CardNotDueError(ValueError):
    """The card is not due today."""


def _clean(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise EmptyTextError("text must not be empty")
    return cleaned


def _commit_deck(session: Session, deck: Deck) -> Deck:
    session.add(deck)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DuplicateDeckNameError(deck.name) from exc
    session.refresh(deck)
    return deck


def list_decks(session: Session) -> list[Deck]:
    return list(session.exec(select(Deck).order_by(Deck.name)).all())


def get_deck(session: Session, deck_id: int) -> Deck | None:
    return session.get(Deck, deck_id)


def create_deck(session: Session, name: str) -> Deck:
    return _commit_deck(session, Deck(name=_clean(name)))


def rename_deck(session: Session, deck: Deck, name: str) -> Deck:
    deck.name = _clean(name)
    return _commit_deck(session, deck)


def delete_deck(session: Session, deck: Deck) -> None:
    session.delete(deck)
    session.commit()


def list_cards(session: Session, deck: Deck) -> list[Card]:
    return list(session.exec(select(Card).where(Card.deck_id == deck.id).order_by(Card.id)).all())


def get_card(session: Session, card_id: int) -> Card | None:
    return session.get(Card, card_id)


def create_card(session: Session, deck: Deck, front: str, back: str, today: date) -> Card:
    card = Card(deck_id=deck.id, front=_clean(front), back=_clean(back), due_date=today)
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


def update_card(
    session: Session, card: Card, front: str | None = None, back: str | None = None
) -> Card:
    # Box and due date stay unchanged when editing.
    # Check both texts first so an error leaves nothing half changed.
    new_front = card.front if front is None else _clean(front)
    new_back = card.back if back is None else _clean(back)
    card.front, card.back = new_front, new_back
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


def delete_card(session: Session, card: Card) -> None:
    session.delete(card)
    session.commit()


def _as_utc(moment: datetime) -> datetime:
    # Timestamps without a time zone (e.g. from a form) are treated as UTC.
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment


def due_cards(
    session: Session, deck: Deck, today: date, started: datetime | None = None
) -> list[Card]:
    """Due cards of a deck, lowest box first.

    With ``started``, cards already seen in this study session are left out.
    """
    statement = select(Card).where(Card.deck_id == deck.id, Card.due_date <= today)
    if started is not None:
        statement = statement.where(
            or_(Card.last_reviewed_at.is_(None), Card.last_reviewed_at < _as_utc(started))
        )
    return list(session.exec(statement.order_by(Card.box, Card.due_date, Card.id)).all())


def is_pending(card: Card, today: date, started: datetime) -> bool:
    """Whether the card may still be answered in the session that began at ``started``."""
    if not leitner.is_due(card.due_date, today):
        return False
    return card.last_reviewed_at is None or card.last_reviewed_at < _as_utc(started)


def review_card(session: Session, card: Card, known: bool, today: date, now: datetime) -> Card:
    if not leitner.is_due(card.due_date, today):
        raise CardNotDueError(card.id)
    card.box, card.due_date = leitner.review(card.box, known, today)
    card.last_reviewed_at = _as_utc(now)
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


@dataclass
class DeckStats:
    boxes: dict[int, int]
    total: int
    due_today: int


def deck_stats(session: Session, deck: Deck, today: date) -> DeckStats:
    # Prefill all boxes so empty boxes show up as 0.
    boxes = dict.fromkeys(leitner.BOX_INTERVALS, 0)
    rows = session.exec(
        select(Card.box, func.count()).where(Card.deck_id == deck.id).group_by(Card.box)
    ).all()
    boxes.update(dict(rows))
    due_today = session.exec(
        select(func.count()).where(Card.deck_id == deck.id, Card.due_date <= today)
    ).one()
    return DeckStats(boxes=boxes, total=sum(boxes.values()), due_today=due_today)


def due_counts(session: Session, today: date) -> dict[int, int]:
    """Number of cards due today per deck ID; decks without due cards are missing."""
    rows = session.exec(
        select(Card.deck_id, func.count()).where(Card.due_date <= today).group_by(Card.deck_id)
    ).all()
    return dict(rows)
