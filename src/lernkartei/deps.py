from datetime import date, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from lernkartei import services
from lernkartei.db import get_session
from lernkartei.models import Card, Deck, utc_now


def get_today() -> date:
    # Als Dependency, damit Tests ein festes Datum einsetzen können.
    return date.today()


def get_now() -> datetime:
    return utc_now()


SessionDep = Annotated[Session, Depends(get_session)]
TodayDep = Annotated[date, Depends(get_today)]
NowDep = Annotated[datetime, Depends(get_now)]


def deck_or_404(deck_id: int, session: SessionDep) -> Deck:
    deck = services.get_deck(session, deck_id)
    if deck is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck nicht gefunden")
    return deck


def card_or_404(card_id: int, session: SessionDep) -> Card:
    card = services.get_card(session, card_id)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Karte nicht gefunden")
    return card


DeckDep = Annotated[Deck, Depends(deck_or_404)]
CardDep = Annotated[Card, Depends(card_or_404)]
