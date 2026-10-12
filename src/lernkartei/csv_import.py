"""CSV-Import im Format ``vorne;hinten`` – eine Karte pro Zeile, keine Kopfzeile."""

import csv
import io
from dataclasses import dataclass, field
from datetime import date

from sqlmodel import Session, select

from lernkartei.models import Card, Deck

DELIMITER = ";"
MAX_UPLOAD_BYTES = 1_000_000


@dataclass
class RowError:
    line: int
    message: str


@dataclass
class ParsedCsv:
    rows: list[tuple[str, str]] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)


@dataclass
class ImportResult:
    imported: int
    skipped: int
    errors: list[RowError]


def decode(data: bytes) -> str:
    """UTF-8 (mit oder ohne BOM), ersatzweise Windows-1252, wie es Excel exportiert."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def parse_csv(text: str) -> ParsedCsv:
    """Zerlegt den Text in Karten und meldet fehlerhafte Zeilen mit Zeilennummer."""
    parsed = ParsedCsv()
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=DELIMITER)
    line = 1
    while True:
        try:
            fields = next(reader)
        except StopIteration:
            break
        except csv.Error:
            parsed.errors.append(RowError(line, "Zeile ist kein gültiges CSV."))
            line = reader.line_num + 1
            continue
        start_line, line = line, reader.line_num + 1

        fields = [value.strip() for value in fields]
        if not any(fields):
            if len(fields) > 1:
                parsed.errors.append(RowError(start_line, "Vorder- und Rückseite sind leer."))
            # Leerzeilen werden stillschweigend übergangen.
            continue
        if len(fields) != 2:
            parsed.errors.append(
                RowError(
                    start_line,
                    f"Erwartet 2 Spalten (vorne;hinten), gefunden: {len(fields)}.",
                )
            )
            continue
        front, back = fields
        if not front or not back:
            parsed.errors.append(RowError(start_line, "Vorder- oder Rückseite ist leer."))
            continue
        parsed.rows.append((front, back))
    return parsed


def import_cards(
    session: Session, deck: Deck, rows: list[tuple[str, str]], today: date
) -> tuple[int, int]:
    """Legt neue Karten an und gibt (importiert, übersprungen) zurück.

    Als Duplikat gilt eine Karte, deren Vorder- und Rückseite im Deck oder weiter
    oben in derselben Datei schon vorkommen.
    """
    seen = set(session.exec(select(Card.front, Card.back).where(Card.deck_id == deck.id)).all())
    imported = skipped = 0
    for row in rows:
        if row in seen:
            skipped += 1
            continue
        seen.add(row)
        front, back = row
        session.add(Card(deck_id=deck.id, front=front, back=back, due_date=today))
        imported += 1
    session.commit()
    return imported, skipped


def import_csv(session: Session, deck: Deck, data: bytes, today: date) -> ImportResult:
    parsed = parse_csv(decode(data))
    imported, skipped = import_cards(session, deck, parsed.rows, today)
    return ImportResult(imported=imported, skipped=skipped, errors=parsed.errors)
