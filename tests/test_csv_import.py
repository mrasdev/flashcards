import re

import pytest
from sqlmodel import select

from flashcards.csv_import import MAX_UPLOAD_BYTES, decode, import_csv, parse_csv
from flashcards.models import Card, Deck
from tests.conftest import TODAY

HTMX = {"HX-Request": "true"}


# --- Parser (reine Funktion) -------------------------------------------------


def test_parse_valid_rows():
    parsed = parse_csv("hola;hallo\nadiós;tschüss\n")

    assert parsed.rows == [("hola", "hallo"), ("adiós", "tschüss")]
    assert parsed.errors == []


def test_parse_without_trailing_newline_and_with_crlf():
    parsed = parse_csv("hola;hallo\r\nadiós;tschüss")

    assert parsed.rows == [("hola", "hallo"), ("adiós", "tschüss")]


def test_parse_trims_whitespace():
    assert parse_csv("  hola ;  hallo  \n").rows == [("hola", "hallo")]


def test_parse_quoted_fields_may_contain_delimiter_quotes_and_newlines():
    text = '"uno; dos";"eins; zwei"\n"er sagt ""hola""";"Zeile 1\nZeile 2"\n'

    parsed = parse_csv(text)

    assert parsed.rows == [
        ("uno; dos", "eins; zwei"),
        ('er sagt "hola"', "Zeile 1\nZeile 2"),
    ]
    assert parsed.errors == []


def test_parse_ignores_blank_lines_and_keeps_line_numbers():
    parsed = parse_csv("hola;hallo\n\n   \nnur eine Spalte\nadiós;tschüss\n")

    assert parsed.rows == [("hola", "hallo"), ("adiós", "tschüss")]
    assert [error.line for error in parsed.errors] == [4]


@pytest.mark.parametrize(
    ("line", "fragment"),
    [
        ("nur eine Spalte", "found: 1"),
        ("a;b;c", "found: 3"),
        (";hallo", "Front or back is empty"),
        ("hola;", "Front or back is empty"),
        ("hola;   ", "Front or back is empty"),
        (";", "Front and back are empty"),
    ],
)
def test_parse_reports_invalid_rows(line, fragment):
    parsed = parse_csv(f"hola;hallo\n{line}\n")

    assert parsed.rows == [("hola", "hallo")]
    assert len(parsed.errors) == 1
    assert parsed.errors[0].line == 2
    assert fragment in parsed.errors[0].message


def test_parse_line_number_after_multiline_field():
    parsed = parse_csv('"a\nb";c\nkaputt\n')

    assert parsed.rows == [("a\nb", "c")]
    assert [error.line for error in parsed.errors] == [3]


def test_parse_empty_text():
    parsed = parse_csv("")

    assert parsed.rows == []
    assert parsed.errors == []


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp1252"])
def test_decode_handles_excel_encodings(encoding):
    data = "Übung;größer\n".encode(encoding)

    assert parse_csv(decode(data)).rows == [("Übung", "größer")]


# --- Import in die Datenbank -------------------------------------------------


@pytest.fixture
def db_deck(session):
    deck = Deck(name="Spanisch")
    session.add(deck)
    session.commit()
    session.refresh(deck)
    return deck


def cards_of(session, deck):
    return session.exec(select(Card).where(Card.deck_id == deck.id).order_by(Card.id)).all()


def test_import_creates_cards_in_first_box_due_today(session, db_deck):
    result = import_csv(session, db_deck, "hola;hallo\nadiós;tschüss\n".encode(), TODAY)

    assert (result.imported, result.skipped, result.errors) == (2, 0, [])
    cards = cards_of(session, db_deck)
    assert [(card.front, card.back) for card in cards] == [("hola", "hallo"), ("adiós", "tschüss")]
    assert all(card.box == 1 and card.due_date == TODAY for card in cards)


def test_import_skips_duplicates_in_deck_and_within_file(session, db_deck):
    session.add(Card(deck_id=db_deck.id, front="hola", back="hallo"))
    session.commit()

    result = import_csv(
        session, db_deck, b"hola;hallo\nadios;tschuess\nadios;tschuess\nhola;guten Tag\n", TODAY
    )

    assert (result.imported, result.skipped) == (2, 2)
    assert [(card.front, card.back) for card in cards_of(session, db_deck)] == [
        ("hola", "hallo"),
        ("adios", "tschuess"),
        ("hola", "guten Tag"),
    ]


def test_second_import_of_same_file_adds_nothing(session, db_deck):
    data = b"hola;hallo\nadios;tschuess\n"
    import_csv(session, db_deck, data, TODAY)

    result = import_csv(session, db_deck, data, TODAY)

    assert (result.imported, result.skipped) == (0, 2)
    assert len(cards_of(session, db_deck)) == 2


def test_import_keeps_valid_rows_when_others_are_invalid(session, db_deck):
    result = import_csv(session, db_deck, b"hola;hallo\nkaputt\na;b;c\nadios;tschuess\n", TODAY)

    assert (result.imported, result.skipped) == (2, 0)
    assert [error.line for error in result.errors] == [2, 3]


def test_same_card_in_other_deck_is_not_a_duplicate(session, db_deck):
    other = Deck(name="Englisch")
    session.add(other)
    session.commit()
    session.add(Card(deck_id=other.id, front="hola", back="hallo"))
    session.commit()

    result = import_csv(session, db_deck, b"hola;hallo\n", TODAY)

    assert (result.imported, result.skipped) == (1, 0)


# --- API ---------------------------------------------------------------------


def upload(client, url, content, **kwargs):
    return client.post(url, files={"file": ("karten.csv", content, "text/csv")}, **kwargs)


def test_api_import_returns_result(client, deck):
    content = "hola;hallo\nÜbung;größer\nkaputt\nhola;hallo\n".encode("cp1252")

    response = upload(client, f"/api/decks/{deck['id']}/import", content)

    assert response.status_code == 200
    body = response.json()
    assert (body["imported"], body["skipped"]) == (2, 1)
    assert [error["line"] for error in body["errors"]] == [3]
    cards = client.get(f"/api/decks/{deck['id']}/cards").json()
    assert [card["front"] for card in cards] == ["hola", "Übung"]
    assert all(card["box"] == 1 and card["due_date"] == TODAY.isoformat() for card in cards)


def test_api_import_errors(client, deck):
    assert upload(client, "/api/decks/999/import", b"a;b\n").status_code == 404
    assert client.post(f"/api/decks/{deck['id']}/import").status_code == 422
    too_large = b"a" * (MAX_UPLOAD_BYTES + 1)
    assert upload(client, f"/api/decks/{deck['id']}/import", too_large).status_code == 413
    assert client.get(f"/api/decks/{deck['id']}/cards").json() == []


# --- Oberfläche --------------------------------------------------------------


def test_deck_page_contains_import_form(client, deck):
    html = client.get(f"/decks/{deck['id']}").text

    assert "CSV import" in html
    assert f'hx-post="/decks/{deck["id"]}/import"' in html
    assert 'hx-encoding="multipart/form-data"' in html
    assert 'type="file"' in html
    assert "Import finished" not in html


def test_page_import_with_htmx_shows_result_cards_and_stats(client, deck):
    content = "hola;hallo\nadiós;tschüss\nkaputt\nhola;hallo\n".encode()

    response = upload(client, f"/decks/{deck['id']}/import", content, headers=HTMX)

    assert response.status_code == 200
    html = response.text
    assert "<html" not in html
    assert 'id="cards"' in html
    assert "Import finished" in html
    counts = dict(re.findall(r'data-import="(\w+)">(\d+)<', html))
    assert counts == {"imported": "2", "skipped": "1", "errors": "1"}
    assert "Line 3:" in html
    assert "adiós" in html
    assert re.search(r'data-stat="total">2<', html)


def test_page_import_without_htmx_renders_full_page(client, deck):
    response = upload(client, f"/decks/{deck['id']}/import", b"hola;hallo\n")

    assert response.status_code == 200
    assert "<html" in response.text
    assert "Import finished" in response.text


def test_page_import_without_file_shows_error(client, deck):
    response = client.post(f"/decks/{deck['id']}/import", headers=HTMX)

    assert response.status_code == 200
    assert "Please choose a CSV file." in response.text


def test_page_import_of_too_large_file_shows_error(client, deck):
    content = b"a" * (MAX_UPLOAD_BYTES + 1)

    response = upload(client, f"/decks/{deck['id']}/import", content, headers=HTMX)

    assert "The file is larger than 1 MB." in response.text
    assert client.get(f"/api/decks/{deck['id']}/cards").json() == []


def test_page_import_for_unknown_deck_returns_404(client):
    assert upload(client, "/decks/999/import", b"a;b\n").status_code == 404
