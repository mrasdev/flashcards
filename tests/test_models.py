from datetime import date

import pytest
from sqlalchemy import delete, inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from lernkartei.db import init_db, make_engine
from lernkartei.models import Card, Deck


def make_deck(session, name="Spanisch"):
    deck = Deck(name=name)
    session.add(deck)
    session.commit()
    session.refresh(deck)
    return deck


def test_new_card_starts_in_box_one_and_is_due_today(session):
    deck = make_deck(session)
    card = Card(deck_id=deck.id, front="hola", back="hallo")
    session.add(card)
    session.commit()
    session.refresh(card)

    assert card.box == 1
    assert card.due_date == date.today()
    assert card.last_reviewed_at is None
    assert card.deck == deck


def test_deleting_deck_removes_its_cards(session):
    deck = make_deck(session)
    other = make_deck(session, name="Englisch")
    session.add(Card(deck_id=deck.id, front="hola", back="hallo"))
    session.add(Card(deck_id=other.id, front="dog", back="Hund"))
    session.commit()

    session.delete(deck)
    session.commit()

    assert [card.front for card in session.exec(select(Card)).all()] == ["dog"]


def test_database_cascades_on_raw_delete(session):
    deck = make_deck(session)
    session.add(Card(deck_id=deck.id, front="hola", back="hallo"))
    session.commit()

    session.exec(delete(Deck).where(Deck.id == deck.id))
    session.commit()

    assert session.exec(select(Card)).all() == []


def test_duplicate_deck_name_is_rejected(session):
    make_deck(session)
    session.add(Deck(name="Spanisch"))

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize("box", [0, 6])
def test_box_outside_range_is_rejected(session, box):
    deck = make_deck(session)
    session.add(Card(deck_id=deck.id, front="hola", back="hallo", box=box))

    with pytest.raises(IntegrityError):
        session.commit()


def test_card_requires_existing_deck(session):
    session.add(Card(deck_id=999, front="hola", back="hallo"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_init_db_creates_file_with_both_tables(tmp_path):
    db_file = tmp_path / "lernkartei.db"
    engine = make_engine(f"sqlite:///{db_file.as_posix()}")

    init_db(engine)

    assert db_file.exists()
    assert set(inspect(engine).get_table_names()) == {"deck", "card"}
    engine.dispose()
