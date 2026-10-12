from fastapi import APIRouter, HTTPException, status

from lernkartei import services
from lernkartei.deps import CardDep, DeckDep, SessionDep, TodayDep
from lernkartei.schemas import CardCreate, CardRead, CardUpdate, DeckCreate, DeckRead, DeckUpdate

router = APIRouter(prefix="/api")


def _duplicate_name() -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, "Ein Deck mit diesem Namen existiert bereits")


@router.get("/decks", response_model=list[DeckRead], tags=["Decks"])
def list_decks(session: SessionDep):
    return services.list_decks(session)


@router.post(
    "/decks", response_model=DeckRead, status_code=status.HTTP_201_CREATED, tags=["Decks"]
)
def create_deck(data: DeckCreate, session: SessionDep):
    try:
        return services.create_deck(session, data.name)
    except services.DuplicateDeckNameError:
        raise _duplicate_name() from None


@router.get("/decks/{deck_id}", response_model=DeckRead, tags=["Decks"])
def read_deck(deck: DeckDep):
    return deck


@router.patch("/decks/{deck_id}", response_model=DeckRead, tags=["Decks"])
def rename_deck(data: DeckUpdate, deck: DeckDep, session: SessionDep):
    try:
        return services.rename_deck(session, deck, data.name)
    except services.DuplicateDeckNameError:
        raise _duplicate_name() from None


@router.delete("/decks/{deck_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Decks"])
def delete_deck(deck: DeckDep, session: SessionDep) -> None:
    services.delete_deck(session, deck)


@router.get("/decks/{deck_id}/cards", response_model=list[CardRead], tags=["Karten"])
def list_cards(deck: DeckDep, session: SessionDep):
    return services.list_cards(session, deck)


@router.post(
    "/decks/{deck_id}/cards",
    response_model=CardRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Karten"],
)
def create_card(data: CardCreate, deck: DeckDep, session: SessionDep, today: TodayDep):
    return services.create_card(session, deck, data.front, data.back, today)


@router.get("/cards/{card_id}", response_model=CardRead, tags=["Karten"])
def read_card(card: CardDep):
    return card


@router.patch("/cards/{card_id}", response_model=CardRead, tags=["Karten"])
def update_card(data: CardUpdate, card: CardDep, session: SessionDep):
    return services.update_card(session, card, front=data.front, back=data.back)


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Karten"])
def delete_card(card: CardDep, session: SessionDep) -> None:
    services.delete_card(session, card)
