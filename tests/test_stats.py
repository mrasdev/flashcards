import re

HTMX = {"HX-Request": "true"}


def get_stats(client, deck_id):
    response = client.get(f"/api/decks/{deck_id}/stats")
    assert response.status_code == 200
    return response.json()


def cell(html, attribute, value):
    """Liest den Inhalt der Tabellenzelle mit dem angegebenen data-Attribut."""
    match = re.search(rf'<td {attribute}="{value}">(?:<strong>)?(\d+)', html)
    assert match, f"cell {attribute}={value} not found"
    return int(match.group(1))


# --- API ---------------------------------------------------------------------


def test_stats_of_empty_deck_are_all_zero(client, deck):
    assert get_stats(client, deck["id"]) == {
        "boxes": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
        "total": 0,
        "due_today": 0,
    }


def test_stats_count_cards_per_box(client, deck, add_card):
    add_card("a", box=1)
    add_card("b", box=1)
    add_card("c", box=3, due_in_days=2)
    add_card("d", box=5, due_in_days=10)

    stats = get_stats(client, deck["id"])

    assert stats["boxes"] == {"1": 2, "2": 0, "3": 1, "4": 0, "5": 1}
    assert stats["total"] == 4


def test_due_today_includes_today_and_overdue_but_not_tomorrow(client, deck, add_card):
    add_card("heute")
    add_card("überfällig", box=4, due_in_days=-5)
    add_card("morgen", box=2, due_in_days=1)

    assert get_stats(client, deck["id"])["due_today"] == 2


def test_stats_ignore_cards_of_other_decks(client, deck, add_card):
    other = client.post("/api/decks", json={"name": "Englisch"}).json()
    add_card("eigen")
    add_card("fremd", deck_id=other["id"])
    add_card("fremd2", deck_id=other["id"])

    assert get_stats(client, deck["id"])["total"] == 1
    assert get_stats(client, other["id"])["total"] == 2


def test_stats_change_after_review(client, deck, add_card):
    first = add_card("a")
    second = add_card("b")

    client.post(f"/api/cards/{first}/review", json={"known": True})
    client.post(f"/api/cards/{second}/review", json={"known": False})

    stats = get_stats(client, deck["id"])
    assert stats["boxes"] == {"1": 1, "2": 1, "3": 0, "4": 0, "5": 0}
    assert stats["due_today"] == 1


def test_stats_of_unknown_deck_return_404(client):
    assert client.get("/api/decks/999/stats").status_code == 404


# --- Oberfläche --------------------------------------------------------------


def test_deck_page_shows_stats(client, deck, add_card):
    add_card("a", box=1)
    add_card("b", box=2, due_in_days=1)
    add_card("c", box=2, due_in_days=-1)

    html = client.get(f"/decks/{deck['id']}").text

    assert "Statistik" in html
    assert [cell(html, "data-box", box) for box in range(1, 6)] == [1, 2, 0, 0, 0]
    assert cell(html, "data-stat", "total") == 3
    assert cell(html, "data-stat", "due-today") == 2
    assert "Lernen (2 fällig)" in html


def test_deck_page_of_empty_deck_shows_zero_stats(client, deck):
    html = client.get(f"/decks/{deck['id']}").text

    assert cell(html, "data-stat", "total") == 0
    assert cell(html, "data-stat", "due-today") == 0
    assert "fällig)" not in html


def test_stats_are_refreshed_when_card_is_added(client, deck):
    response = client.post(
        f"/decks/{deck['id']}/cards", data={"front": "hola", "back": "hallo"}, headers=HTMX
    )

    assert cell(response.text, "data-box", 1) == 1
    assert cell(response.text, "data-stat", "due-today") == 1


def test_stats_are_refreshed_when_card_is_deleted(client, deck, add_card):
    card_id = add_card("hola")

    response = client.delete(f"/cards/{card_id}", headers=HTMX)

    assert cell(response.text, "data-stat", "total") == 0


def test_deck_list_shows_due_count_per_deck(client, deck, add_card):
    other = client.post("/api/decks", json={"name": "Englisch"}).json()
    add_card("heute")
    add_card("überfällig", due_in_days=-1)
    add_card("morgen", due_in_days=1)

    html = client.get("/").text

    assert "Heute fällig" in html
    rows = {
        int(deck_id): int(count)
        for deck_id, count in re.findall(
            r'<tr id="deck-(\d+)">.*?data-stat="due-today">(\d+)<', html, flags=re.S
        )
    }
    assert rows == {deck["id"]: 2, other["id"]: 0}


def test_deck_row_partial_contains_due_count(client, deck, add_card):
    add_card("heute")

    response = client.get(f"/decks/{deck['id']}/row", headers=HTMX)

    assert cell(response.text, "data-stat", "due-today") == 1
