import pytest

HTMX = {"HX-Request": "true"}


def create_deck(client, name="Spanish"):
    return client.post("/api/decks", json={"name": name}).json()


def create_card(client, deck, front="hola", back="hello"):
    return client.post(
        f"/api/decks/{deck['id']}/cards", json={"front": front, "back": back}
    ).json()


def is_full_page(response):
    return "<html" in response.text


# --- Deck list ---------------------------------------------------------------


def test_deck_list_shows_hint_when_empty(client):
    response = client.get("/")

    assert response.status_code == 200
    assert is_full_page(response)
    assert "No decks yet" in response.text


def test_deck_list_shows_decks(client):
    deck = create_deck(client)

    response = client.get("/")

    assert "Spanish" in response.text
    assert f'href="/decks/{deck["id"]}"' in response.text


def test_deck_name_is_escaped(client):
    create_deck(client, "<b>bold</b>")

    response = client.get("/")

    assert "<b>bold</b>" not in response.text
    assert "&lt;b&gt;bold&lt;/b&gt;" in response.text


def test_create_deck_without_htmx_redirects(client):
    response = client.post("/decks", data={"name": "Spanish"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert "Spanish" in client.get("/").text


def test_create_deck_with_htmx_returns_only_partial(client):
    response = client.post("/decks", data={"name": "Spanish"}, headers=HTMX)

    assert response.status_code == 200
    assert not is_full_page(response)
    assert 'id="decks"' in response.text
    assert "Spanish" in response.text


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("   ", "Please enter a name."),
        ("Spanish", "A deck with this name already exists."),
    ],
)
def test_create_deck_shows_error(client, name, message):
    create_deck(client)

    response = client.post("/decks", data={"name": name}, headers=HTMX)

    assert response.status_code == 200
    assert message in response.text
    assert len(client.get("/api/decks").json()) == 1


def test_create_deck_error_without_htmx_renders_full_page(client):
    response = client.post("/decks", data={"name": ""})

    assert response.status_code == 422
    assert is_full_page(response)
    assert "Please enter a name." in response.text


def test_deck_edit_form_is_prefilled(client):
    deck = create_deck(client)

    response = client.get(f"/decks/{deck['id']}/edit", headers=HTMX)

    assert response.status_code == 200
    assert not is_full_page(response)
    assert 'value="Spanish"' in response.text
    assert f'hx-put="/decks/{deck["id"]}"' in response.text


def test_deck_row_partial_for_cancel(client):
    deck = create_deck(client)

    response = client.get(f"/decks/{deck['id']}/row", headers=HTMX)

    assert response.status_code == 200
    assert response.text.lstrip().startswith("<tr")
    assert "Rename" in response.text


def test_rename_deck_returns_row(client):
    deck = create_deck(client)

    response = client.put(f"/decks/{deck['id']}", data={"name": "Español"}, headers=HTMX)

    assert response.status_code == 200
    assert response.text.lstrip().startswith("<tr")
    assert "Español" in response.text
    assert client.get(f"/api/decks/{deck['id']}").json()["name"] == "Español"


def test_rename_deck_to_existing_name_shows_error_and_keeps_input(client):
    create_deck(client, "French")
    deck = create_deck(client, "Spanish")

    response = client.put(f"/decks/{deck['id']}", data={"name": "French"}, headers=HTMX)

    assert response.status_code == 200
    assert "A deck with this name already exists." in response.text
    assert 'value="French"' in response.text
    assert client.get(f"/api/decks/{deck['id']}").json()["name"] == "Spanish"


def test_delete_deck_returns_updated_section(client):
    deck = create_deck(client)
    card = create_card(client, deck)

    response = client.delete(f"/decks/{deck['id']}", headers=HTMX)

    assert response.status_code == 200
    assert not is_full_page(response)
    assert "No decks yet" in response.text
    assert client.get(f"/api/cards/{card['id']}").status_code == 404


def test_delete_button_asks_for_confirmation(client):
    create_deck(client)

    assert "hx-confirm=" in client.get("/").text


# --- Deck page with cards ----------------------------------------------------


def test_deck_detail_shows_cards(client):
    deck = create_deck(client)
    create_card(client, deck)

    response = client.get(f"/decks/{deck['id']}")

    assert response.status_code == 200
    assert is_full_page(response)
    assert "<h1>Spanish</h1>" in response.text
    assert "hola" in response.text
    assert "hello" in response.text


def test_deck_detail_shows_hint_when_empty(client):
    deck = create_deck(client)

    assert "This deck has no cards yet." in client.get(f"/decks/{deck['id']}").text


def test_create_card_with_htmx_returns_only_partial(client):
    deck = create_deck(client)

    response = client.post(
        f"/decks/{deck['id']}/cards", data={"front": "hola", "back": "hello"}, headers=HTMX
    )

    assert response.status_code == 200
    assert not is_full_page(response)
    assert 'id="cards"' in response.text
    assert "hola" in response.text
    assert len(client.get(f"/api/decks/{deck['id']}/cards").json()) == 1


def test_create_card_without_htmx_redirects(client):
    deck = create_deck(client)

    response = client.post(
        f"/decks/{deck['id']}/cards",
        data={"front": "hola", "back": "hello"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == f"/decks/{deck['id']}"


def test_create_card_with_empty_side_shows_error_and_keeps_input(client):
    deck = create_deck(client)

    response = client.post(
        f"/decks/{deck['id']}/cards", data={"front": "hola", "back": " "}, headers=HTMX
    )

    assert response.status_code == 200
    assert "Front and back must not be empty." in response.text
    assert 'value="hola"' in response.text
    assert client.get(f"/api/decks/{deck['id']}/cards").json() == []


def test_card_edit_form_is_prefilled(client):
    deck = create_deck(client)
    card = create_card(client, deck)

    response = client.get(f"/cards/{card['id']}/edit", headers=HTMX)

    assert response.status_code == 200
    assert 'value="hola"' in response.text
    assert 'value="hello"' in response.text


def test_card_row_partial_for_cancel(client):
    deck = create_deck(client)
    card = create_card(client, deck)

    response = client.get(f"/cards/{card['id']}/row", headers=HTMX)

    assert response.text.lstrip().startswith("<tr")
    assert "Edit" in response.text


def test_update_card_returns_row(client):
    deck = create_deck(client)
    card = create_card(client, deck)

    response = client.put(
        f"/cards/{card['id']}", data={"front": "adiós", "back": "goodbye"}, headers=HTMX
    )

    assert response.status_code == 200
    assert response.text.lstrip().startswith("<tr")
    assert "adiós" in response.text
    stored = client.get(f"/api/cards/{card['id']}").json()
    assert (stored["front"], stored["back"]) == ("adiós", "goodbye")


def test_update_card_with_empty_side_changes_nothing(client):
    deck = create_deck(client)
    card = create_card(client, deck)

    response = client.put(
        f"/cards/{card['id']}", data={"front": "adiós", "back": ""}, headers=HTMX
    )

    assert "Front and back must not be empty." in response.text
    stored = client.get(f"/api/cards/{card['id']}").json()
    assert (stored["front"], stored["back"]) == ("hola", "hello")


def test_delete_card_returns_updated_section(client):
    deck = create_deck(client)
    card = create_card(client, deck)

    response = client.delete(f"/cards/{card['id']}", headers=HTMX)

    assert response.status_code == 200
    assert "This deck has no cards yet." in response.text
    assert client.get(f"/api/cards/{card['id']}").status_code == 404


# --- Miscellaneous -----------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/decks/999"),
        ("get", "/decks/999/edit"),
        ("put", "/decks/999"),
        ("delete", "/decks/999"),
        ("post", "/decks/999/cards"),
        ("get", "/cards/999/edit"),
        ("put", "/cards/999"),
        ("delete", "/cards/999"),
    ],
)
def test_unknown_deck_or_card_returns_404(client, method, path):
    assert client.request(method, path).status_code == 404


@pytest.mark.parametrize("asset", ["htmx.min.js", "pico.min.css", "app.css"])
def test_static_assets_are_served(client, asset):
    assert client.get(f"/static/{asset}").status_code == 200
