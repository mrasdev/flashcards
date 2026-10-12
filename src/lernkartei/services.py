"""Datenbankoperationen, die JSON-API und HTML-Oberfläche gemeinsam nutzen."""

from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from lernkartei.models import Card, Deck


class EmptyTextError(ValueError):
    """Ein Pflichttext ist leer oder besteht nur aus Leerzeichen."""


class DuplicateDeckNameError(ValueError):
    """Es gibt bereits ein Deck mit diesem Namen."""


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
    # Fach und Fälligkeit bleiben beim Bearbeiten unverändert.
    # Erst beide Texte prüfen, damit bei einem Fehler nichts halb geändert ist.
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
