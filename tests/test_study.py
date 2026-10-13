import re
from datetime import timedelta
from html.parser import HTMLParser

import pytest

from tests.conftest import TODAY

HTMX = {"HX-Request": "true"}


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
    other = client.post("/api/decks", json={"name": "French"}).json()
    add_card("today")
    add_card("overdue", box=3, due_in_days=-2)
    add_card("tomorrow", box=2, due_in_days=1)
    add_card("foreign", deck_id=other["id"])

    response = client.get(f"/api/decks/{deck['id']}/due")

    assert response.status_code == 200
    assert {card["front"] for card in response.json()} == {"today", "overdue"}


def test_due_is_ordered_by_box_then_due_date_then_id(client, deck, add_card):
    add_card("box3", box=3)
    add_card("box1-today", box=1)
    add_card("box1-yesterday", box=1, due_in_days=-1)
    add_card("box1-today-2", box=1)

    fronts = [card["front"] for card in client.get(f"/api/decks/{deck['id']}/due").json()]

    assert fronts == ["box1-yesterday", "box1-today", "box1-today-2", "box3"]


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


# --- UI ----------------------------------------------------------------------


def test_deck_page_links_to_study_mode(client, deck):
    assert f'href="/decks/{deck["id"]}/study"' in client.get(f"/decks/{deck['id']}").text


def test_study_page_shows_first_due_card(client, deck, add_card, clock):
    add_card("box2", box=2)
    first = add_card("hola", back="hello", box=1)
    add_card("tomorrow", due_in_days=1)

    response = client.get(f"/decks/{deck['id']}/study")

    assert response.status_code == 200
    assert "<html" in response.text
    assert "hola" in response.text
    assert "hello" in response.text
    assert "Reveal" in response.text
    assert "2 cards left in this session" in response.text
    assert f'action="/cards/{first}/answer"' in response.text
    assert f'value="{clock.now.isoformat()}"' in response.text
    assert "tomorrow" not in response.text


def test_study_page_for_deck_without_due_cards(client, deck, add_card):
    add_card("tomorrow", due_in_days=1)

    response = client.get(f"/decks/{deck['id']}/study")

    assert response.status_code == 200
    assert "Done for today!" in response.text
    assert "tomorrow" not in response.text


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
    assert "1 card left in this session" in response.text
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

    assert "Done for today!" in response.text
    assert client.get(f"/api/decks/{deck['id']}/due").json() == []


def test_unknown_card_is_not_repeated_in_same_session(client, deck, add_card, clock):
    card_id = add_card("hola", box=3)
    started = clock.now
    clock.tick()

    response = answer(client, card_id, False, started, headers=HTMX)

    assert "Session finished." in response.text
    assert "1 card you did not know comes" in response.text
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

    # The card is back in box 1 and due; a second click must not promote it.
    response = answer(client, card_id, True, started, headers=HTMX)

    assert response.status_code == 200
    stored = get_card(client, card_id)
    assert stored["box"] == 1
    assert stored["last_reviewed_at"] == first_review


def test_answer_for_unknown_card_returns_404(client, clock):
    assert answer(client, 999, True, clock.now).status_code == 404


# --- Keyboard control --------------------------------------------------------

KEYBOARD_SCRIPT = '<script src="/static/study.js" defer></script>'


def tag_with(html, tag, attribute):
    """Return the first opening tag that contains the given attribute."""
    for match in re.finditer(rf"<{tag}\b[^>]*>", html):
        if attribute in match.group(0):
            return match.group(0)
    raise AssertionError(f"no <{tag}> with {attribute} found")


def has_key_hint(html):
    return 'class="key-hint"' in html


def test_study_page_loads_keyboard_script(client, deck, add_card):
    add_card("hola")

    html = client.get(f"/decks/{deck['id']}/study").text

    assert html.count(KEYBOARD_SCRIPT) == 1


def test_keyboard_script_is_served(client):
    response = client.get("/static/study.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_other_pages_do_not_load_keyboard_script(client, deck):
    assert "study.js" not in client.get("/").text
    assert "study.js" not in client.get(f"/decks/{deck['id']}").text


def test_answer_partial_does_not_reload_script(client, deck, add_card, clock):
    first = add_card("hola")
    add_card("adiós")
    started = clock.now
    clock.tick()

    response = answer(client, first, True, started, headers=HTMX)

    assert "<script" not in response.text


def test_study_page_shows_key_hint(client, deck, add_card):
    add_card("hola")

    html = client.get(f"/decks/{deck['id']}/study").text

    assert has_key_hint(html)
    assert "<kbd>Space</kbd>" in html
    assert "<kbd>K</kbd>" in html
    assert "<kbd>N</kbd>" in html


def test_next_card_partial_shows_key_hint(client, deck, add_card, clock):
    first = add_card("hola")
    add_card("adiós")
    started = clock.now
    clock.tick()

    response = answer(client, first, True, started, headers=HTMX)

    assert "adiós" in response.text
    assert has_key_hint(response.text)


def test_key_hint_is_hidden_when_session_is_over(client, deck, add_card, clock):
    card_id = add_card("hola")
    started = clock.now
    clock.tick()

    postponed = answer(client, card_id, False, started, headers=HTMX)

    assert "Session finished." in postponed.text
    assert not has_key_hint(postponed.text)

    clock.tick()
    started = clock.now
    clock.tick()
    done = answer(client, card_id, True, started, headers=HTMX)

    assert "Done for today!" in done.text
    assert not has_key_hint(done.text)


def test_study_page_without_due_cards_has_no_key_hint(client, deck):
    html = client.get(f"/decks/{deck['id']}/study").text

    assert "Done for today!" in html
    assert not has_key_hint(html)


def test_study_card_has_keyboard_hooks(client, deck, add_card):
    add_card("hola")

    html = client.get(f"/decks/{deck['id']}/study").text

    assert tag_with(html, "details", "data-study-reveal")
    assert 'data-study-key="k"' in tag_with(html, "button", 'value="true"')
    assert 'data-study-key="n"' in tag_with(html, "button", 'value="false"')


VOID_TAGS = {"br", "hr", "img", "input", "link", "meta"}


class KeyButtonFinder(HTMLParser):
    """Record the chain of ancestors for each button with data-study-key."""

    def __init__(self):
        super().__init__()
        self.open_tags = []
        self.ancestors = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "button" and "data-study-key" in attrs:
            self.ancestors[attrs["data-study-key"]] = list(self.open_tags)
        if tag not in VOID_TAGS:
            self.open_tags.append((tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.open_tags) - 1, -1, -1):
            if self.open_tags[index][0] == tag:
                del self.open_tags[index:]
                break


def test_key_buttons_are_nested_in_reveal_details_inside_study(client, deck, add_card):
    add_card("hola")
    finder = KeyButtonFinder()

    finder.feed(client.get(f"/decks/{deck['id']}/study").text)

    # study.js looks up "#study details[data-study-reveal]" and the buttons inside it.
    assert set(finder.ancestors) == {"k", "n"}
    for ancestors in finder.ancestors.values():
        study = [i for i, (_, attrs) in enumerate(ancestors) if attrs.get("id") == "study"]
        reveal = [
            i
            for i, (tag, attrs) in enumerate(ancestors)
            if tag == "details" and "data-study-reveal" in attrs
        ]
        assert study and reveal
        assert study[0] < reveal[0]


def test_keyboard_script_uses_the_template_hooks(client):
    script = client.get("/static/study.js").text

    assert "data-study-reveal" in script
    assert "data-study-key" in script
