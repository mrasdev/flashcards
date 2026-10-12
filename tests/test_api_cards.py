import pytest
from sqlmodel import Session

from lernkartei.models import Card
from tests.conftest import TODAY


@pytest.fixture
def deck(client):
    return client.post("/api/decks", json={"name": "Spanisch"}).json()


def create_card(client, deck, front="hola", back="hallo"):
    response = client.post(f"/api/decks/{deck['id']}/cards", json={"front": front, "back": back})
    assert response.status_code == 201
    return response.json()


def test_create_card_starts_in_box_one_due_today(client, deck):
    response = client.post(
        f"/api/decks/{deck['id']}/cards", json={"front": "  hola ", "back": " hallo  "}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["front"] == "hola"
    assert body["back"] == "hallo"
    assert body["deck_id"] == deck["id"]
    assert body["box"] == 1
    assert body["due_date"] == TODAY.isoformat()
    assert body["last_reviewed_at"] is None


def test_list_cards_only_returns_cards_of_deck(client, deck):
    other = client.post("/api/decks", json={"name": "Englisch"}).json()
    create_card(client, deck, "hola", "hallo")
    create_card(client, deck, "adiós", "tschüss")
    create_card(client, other, "dog", "Hund")

    response = client.get(f"/api/decks/{deck['id']}/cards")

    assert response.status_code == 200
    assert [card["front"] for card in response.json()] == ["hola", "adiós"]


def test_read_card(client, deck):
    card = create_card(client, deck)

    response = client.get(f"/api/cards/{card['id']}")

    assert response.status_code == 200
    assert response.json() == card


def test_update_card_changes_only_given_fields(client, deck):
    card = create_card(client, deck)

    response = client.patch(f"/api/cards/{card['id']}", json={"back": "hallo!"})

    assert response.status_code == 200
    assert response.json()["front"] == "hola"
    assert response.json()["back"] == "hallo!"


def test_update_card_keeps_box_and_due_date(client, deck, engine):
    card = create_card(client, deck)
    with Session(engine) as session:
        stored = session.get(Card, card["id"])
        stored.box = 3
        stored.due_date = TODAY.replace(day=20)
        session.add(stored)
        session.commit()

    response = client.patch(f"/api/cards/{card['id']}", json={"front": "buenos días"})

    assert response.status_code == 200
    assert response.json()["box"] == 3
    assert response.json()["due_date"] == TODAY.replace(day=20).isoformat()


def test_delete_card(client, deck):
    card = create_card(client, deck)

    response = client.delete(f"/api/cards/{card['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/cards/{card['id']}").status_code == 404
    assert client.get(f"/api/decks/{deck['id']}/cards").json() == []


@pytest.mark.parametrize(
    "payload",
    [
        {"front": "", "back": "hallo"},
        {"front": "hola", "back": "   "},
        {"front": "hola"},
        {},
    ],
)
def test_create_card_with_invalid_text_returns_422(client, deck, payload):
    assert client.post(f"/api/decks/{deck['id']}/cards", json=payload).status_code == 422


def test_update_card_with_empty_text_returns_422(client, deck):
    card = create_card(client, deck)

    assert client.patch(f"/api/cards/{card['id']}", json={"front": " "}).status_code == 422
    assert client.get(f"/api/cards/{card['id']}").json()["front"] == "hola"


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/decks/999/cards", None),
        ("post", "/api/decks/999/cards", {"front": "a", "back": "b"}),
        ("get", "/api/cards/999", None),
        ("patch", "/api/cards/999", {"front": "a"}),
        ("delete", "/api/cards/999", None),
    ],
)
def test_unknown_deck_or_card_returns_404(client, method, path, payload):
    response = client.request(method, path, json=payload)

    assert response.status_code == 404
