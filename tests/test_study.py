from datetime import timedelta

import pytest
from sqlmodel import Session

from lernkartei.models import Card
from tests.conftest import TODAY

HTMX = {"HX-Request": "true"}


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


def get_card(client, card_id):
    return client.get(f"/api/cards/{card_id}").json()


def answer(client, card_id, known, started, **kwargs):
    return client.post(
        f"/cards/{card_id}/answer",
        data={"known": "true" if known else "false", "started": started.isoformat()},
        **kwargs,
    )


# --- API ---------------------------------------------------------------------


def test_due_lists_only_due_cards_of_deck(client, deck, add_card):
    other = client.post("/api/decks", json={"name": "Englisch"}).json()
    add_card("heute")
    add_card("überfällig", box=3, due_in_days=-2)
    add_card("morgen", box=2, due_in_days=1)
    add_card("fremd", deck_id=other["id"])

    response = client.get(f"/api/decks/{deck['id']}/due")

    assert response.status_code == 200
    assert {card["front"] for card in response.json()} == {"heute", "überfällig"}


def test_due_is_ordered_by_box_then_due_date_then_id(client, deck, add_card):
    add_card("fach3", box=3)
    add_card("fach1-heute", box=1)
    add_card("fach1-gestern", box=1, due_in_days=-1)
    add_card("fach1-heute-2", box=1)

    fronts = [card["front"] for card in client.get(f"/api/decks/{deck['id']}/due").json()]

    assert fronts == ["fach1-gestern", "fach1-heute", "fach1-heute-2", "fach3"]


@pytest.mark.parametrize(
    ("box", "new_box", "days"),
    [(1, 2, 1), (2, 3, 3), (3, 4, 7), (4, 5, 14), (5, 5, 14)],
)
def test_review_known_moves_card_up(client, add_card, clock, box, new_box, days):
    card_id = add_card("hola", box=box)

    response = client.post(f"/api/cards/{card_id}/review", json={"known": True})

    assert response.status_code == 200
    body = response.json()
    assert body["box"] == new_box
    assert body["due_date"] == (TODAY + timedelta(days=days)).isoformat()
    assert body["last_reviewed_at"] == clock.now.isoformat().replace("+00:00", "Z")


@pytest.mark.parametrize("box", [1, 3, 5])
def test_review_unknown_moves_card_to_first_box(client, add_card, box):
    card_id = add_card("hola", box=box)

    body = client.post(f"/api/cards/{card_id}/review", json={"known": False}).json()

    assert body["box"] == 1
    assert body["due_date"] == TODAY.isoformat()


def test_review_of_card_that_is_not_due_returns_409(client, add_card):
    card_id = add_card("hola", box=2, due_in_days=1)

    response = client.post(f"/api/cards/{card_id}/review", json={"known": True})

    assert response.status_code == 409
    assert get_card(client, card_id)["box"] == 2


def test_review_validation_and_unknown_ids(client, deck, add_card):
    card_id = add_card("hola")

    assert client.post(f"/api/cards/{card_id}/review", json={}).status_code == 422
    assert client.post("/api/cards/999/review", json={"known": True}).status_code == 404
    assert client.get("/api/decks/999/due").status_code == 404


# --- Oberfläche --------------------------------------------------------------


def test_deck_page_links_to_study_mode(client, deck):
    assert f'href="/decks/{deck["id"]}/study"' in client.get(f"/decks/{deck['id']}").text


def test_study_page_shows_first_due_card(client, deck, add_card, clock):
    add_card("fach2", box=2)
    first = add_card("hola", back="hallo", box=1)
    add_card("morgen", due_in_days=1)

    response = client.get(f"/decks/{deck['id']}/study")

    assert response.status_code == 200
    assert "<html" in response.text
    assert "hola" in response.text
    assert "hallo" in response.text
    assert "Aufdecken" in response.text
    assert "Noch 2 Karten in dieser Sitzung" in response.text
    assert f'action="/cards/{first}/answer"' in response.text
    assert f'value="{clock.now.isoformat()}"' in response.text
    assert "morgen" not in response.text


def test_study_page_for_deck_without_due_cards(client, deck, add_card):
    add_card("morgen", due_in_days=1)

    response = client.get(f"/decks/{deck['id']}/study")

    assert response.status_code == 200
    assert "Fertig für heute!" in response.text
    assert "morgen" not in response.text


def test_known_answer_updates_card_and_shows_next(client, deck, add_card, clock):
    first = add_card("hola")
    add_card("adiós")
    started = clock.now
    clock.tick()

    response = answer(client, first, True, started, headers=HTMX)

    assert response.status_code == 200
    assert "<html" not in response.text
    assert 'id="study"' in response.text
    assert "adiós" in response.text
    assert "Noch 1 Karte in dieser Sitzung" in response.text
    stored = get_card(client, first)
    assert stored["box"] == 2
    assert stored["due_date"] == (TODAY + timedelta(days=1)).isoformat()


def test_answer_without_htmx_renders_full_page(client, deck, add_card, clock):
    first = add_card("hola")
    add_card("adiós")
    started = clock.now
    clock.tick()

    response = answer(client, first, True, started)

    assert response.status_code == 200
    assert "<html" in response.text
    assert "adiós" in response.text


def test_session_ends_when_all_cards_known(client, deck, add_card, clock):
    card_ids = [add_card("hola"), add_card("adiós")]
    started = clock.now

    for card_id in card_ids:
        clock.tick()
        response = answer(client, card_id, True, started, headers=HTMX)

    assert "Fertig für heute!" in response.text
    assert client.get(f"/api/decks/{deck['id']}/due").json() == []


def test_unknown_card_is_not_repeated_in_same_session(client, deck, add_card, clock):
    card_id = add_card("hola", box=3)
    started = clock.now
    clock.tick()

    response = answer(client, card_id, False, started, headers=HTMX)

    assert "Sitzung beendet." in response.text
    assert "1 nicht gewusste Karte kommt" in response.text
    assert "hola" not in response.text
    stored = get_card(client, card_id)
    assert stored["box"] == 1
    assert stored["due_date"] == TODAY.isoformat()


def test_unknown_card_returns_in_next_session(client, deck, add_card, clock):
    card_id = add_card("hola")
    started = clock.now
    clock.tick()
    answer(client, card_id, False, started, headers=HTMX)
    clock.tick()

    response = client.get(f"/decks/{deck['id']}/study")

    assert "hola" in response.text
    assert f'action="/cards/{card_id}/answer"' in response.text


def test_repeated_answer_in_same_session_is_ignored(client, deck, add_card, clock):
    card_id = add_card("hola", box=3)
    started = clock.now
    clock.tick()
    answer(client, card_id, False, started, headers=HTMX)
    first_review = get_card(client, card_id)["last_reviewed_at"]
    clock.tick()

    # Die Karte liegt wieder in Fach 1 und ist fällig; ein zweiter Klick darf sie nicht hochstufen.
    response = answer(client, card_id, True, started, headers=HTMX)

    assert response.status_code == 200
    stored = get_card(client, card_id)
    assert stored["box"] == 1
    assert stored["last_reviewed_at"] == first_review


def test_answer_for_unknown_card_returns_404(client, clock):
    assert answer(client, 999, True, clock.now).status_code == 404
