import pytest


def create_deck(client, name="Spanisch"):
    response = client.post("/api/decks", json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_create_deck_returns_201_and_trims_name(client):
    response = client.post("/api/decks", json={"name": "  Spanisch  "})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Spanisch"
    assert isinstance(body["id"], int)


def test_list_decks_is_sorted_by_name(client):
    create_deck(client, "Spanisch")
    create_deck(client, "Englisch")

    response = client.get("/api/decks")

    assert response.status_code == 200
    assert [deck["name"] for deck in response.json()] == ["Englisch", "Spanisch"]


def test_read_deck(client):
    deck = create_deck(client)

    response = client.get(f"/api/decks/{deck['id']}")

    assert response.status_code == 200
    assert response.json() == deck


def test_rename_deck(client):
    deck = create_deck(client)

    response = client.patch(f"/api/decks/{deck['id']}", json={"name": "Español"})

    assert response.status_code == 200
    assert response.json()["name"] == "Español"
    assert client.get(f"/api/decks/{deck['id']}").json()["name"] == "Español"


def test_rename_deck_to_same_name_is_allowed(client):
    deck = create_deck(client)

    response = client.patch(f"/api/decks/{deck['id']}", json={"name": "Spanisch"})

    assert response.status_code == 200


def test_delete_deck(client):
    deck = create_deck(client)

    response = client.delete(f"/api/decks/{deck['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/decks/{deck['id']}").status_code == 404
    assert client.get("/api/decks").json() == []


def test_delete_deck_removes_its_cards(client):
    deck = create_deck(client)
    card = client.post(
        f"/api/decks/{deck['id']}/cards", json={"front": "hola", "back": "hallo"}
    ).json()

    client.delete(f"/api/decks/{deck['id']}")

    assert client.get(f"/api/cards/{card['id']}").status_code == 404


def test_create_duplicate_deck_returns_409(client):
    create_deck(client)

    response = client.post("/api/decks", json={"name": " Spanisch "})

    assert response.status_code == 409
    assert len(client.get("/api/decks").json()) == 1


def test_rename_to_existing_name_returns_409(client):
    create_deck(client, "Spanisch")
    other = create_deck(client, "Englisch")

    response = client.patch(f"/api/decks/{other['id']}", json={"name": "Spanisch"})

    assert response.status_code == 409
    assert client.get(f"/api/decks/{other['id']}").json()["name"] == "Englisch"


@pytest.mark.parametrize("payload", [{"name": ""}, {"name": "   "}, {}])
def test_create_deck_with_invalid_name_returns_422(client, payload):
    assert client.post("/api/decks", json=payload).status_code == 422


def test_rename_deck_with_empty_name_returns_422(client):
    deck = create_deck(client)

    assert client.patch(f"/api/decks/{deck['id']}", json={"name": " "}).status_code == 422


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/decks/999", None),
        ("patch", "/api/decks/999", {"name": "x"}),
        ("delete", "/api/decks/999", None),
    ],
)
def test_unknown_deck_returns_404(client, method, path, payload):
    response = client.request(method, path, json=payload)

    assert response.status_code == 404
