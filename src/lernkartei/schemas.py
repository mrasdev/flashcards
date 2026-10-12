from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

# Eingaben werden getrimmt; leere Texte sind ungültig.
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DeckCreate(BaseModel):
    name: NonEmptyText


class DeckUpdate(BaseModel):
    name: NonEmptyText


class DeckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class CardCreate(BaseModel):
    front: NonEmptyText
    back: NonEmptyText


class CardUpdate(BaseModel):
    front: NonEmptyText | None = None
    back: NonEmptyText | None = None


class CardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deck_id: int
    front: str
    back: str
    box: int
    due_date: date
    last_reviewed_at: datetime | None
    created_at: datetime


class ReviewCreate(BaseModel):
    known: bool
