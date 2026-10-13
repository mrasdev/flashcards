# Umsetzungsplan Flashcards

Karteikarten-Trainer nach Leitner als Webapp (FastAPI, SQLModel/SQLite, Jinja2, HTMX, Pico.css) mit Decks, Karten, Lernmodus, Statistik und CSV-Import. Jede Phase endet mit `ruff check . && pytest` und einem Commit.

## Fortschritt

- [x] Phase 0 – Projektgerüst
- [x] Phase 1 – Datenmodell
- [x] Phase 2 – Leitner-Logik (reine Funktionen)
- [x] Phase 3 – REST-API (Decks und Karten)
- [x] Phase 4 – HTML-Oberfläche (Decks und Karten)
- [x] Phase 5a – Lernmodus
- [x] Phase 5b – Statistik
- [x] Phase 5c – CSV-Import
- [x] Verifikation am Ende
- [x] Tastatursteuerung im Lernmodus

## Entscheidungen

- **Pakete:** zusätzlich zum Stack `uvicorn`, `python-multipart` (Laufzeit) und `httpx` (dev).
- **Fälligkeit:** Kalendertage. Die Karte speichert ein `due_date` (Datum); fällig ist, was `due_date <= heute` hat.
- **Lernsitzung:** Jede Karte erscheint pro Sitzung nur einmal. Nicht gewusste Karten kommen erst beim nächsten Start des Lernmodus wieder.
- **CSV:** keine Kopfzeile, Duplikate (gleiche Vorder- und Rückseite im Deck) werden übersprungen.
- **Tastatursteuerung ohne Abschalter:** Die Einzeltasten J/N im Lernmodus lassen sich nicht abschalten oder umbelegen, wie es WCAG 2.1.4 verlangen würde. Bewusst so entschieden: Einzelnutzer-App, keine Konformitätsanforderung, und J/N wirken nur bei aufgedeckter Karte.

## Annahmen

- Einzelnutzer, keine Anmeldung.
- Kein Migrationswerkzeug: Tabellen per `SQLModel.metadata.create_all` beim Start. DB-Pfad über Umgebungsvariable `FLASHCARDS_DB`, Standard `flashcards.db` (in `.gitignore`).
- Decknamen sind eindeutig; doppelter Name ergibt 409 bzw. Formularfehler.
- Deck löschen löscht dessen Karten mit (Rückfrage per `hx-confirm`).
- Karte bearbeiten ändert Fach und Fälligkeit nicht.
- Karte in Fach 5 gewusst: bleibt in Fach 5, wieder fällig in 14 Tagen.
- Reihenfolge im Lernmodus: niedrigstes Fach zuerst, dann ältestes Fälligkeitsdatum, dann ID.
- HTMX und Pico.css liegen als Dateien in `src/flashcards/static/` (kein CDN, läuft offline).
- "Heute" kommt aus einer FastAPI-Dependency `get_today()`, die Tests überschreiben – keine Zeit-Mocking-Bibliothek nötig.

## Zielstruktur

```
pyproject.toml
.gitignore
src/flashcards/
  __init__.py
  main.py            # App, Router, Static, Lifespan (init_db)
  db.py              # Engine, get_session, init_db
  models.py          # Deck, Card
  schemas.py         # Ein-/Ausgabemodelle der API
  leitner.py         # reine Funktionen
  services.py        # DB-Operationen für API und HTML gemeinsam
  csv_import.py      # Parser (rein) + Import
  deps.py            # get_today
  routers/api.py     # JSON unter /api
  routers/pages.py   # HTML/HTMX
  templates/         # base.html, Seiten, partials/
  static/            # htmx.min.js, pico.min.css
tests/
  conftest.py        # In-Memory-SQLite (StaticPool), Session, TestClient, festes Datum
  test_models.py, test_leitner.py, test_api_decks.py, test_api_cards.py,
  test_pages.py, test_study.py, test_stats.py, test_csv_import.py
```

## Phase 0 – Projektgerüst

- **Dateien:** `pyproject.toml` (setuptools, src-Layout, Abhängigkeiten, `[dev]`-Extra, ruff- und pytest-Konfiguration), `.gitignore`, `src/flashcards/__init__.py`, `main.py` mit `GET /health`, `tests/test_health.py`.
- **Tests:** `/health` liefert 200.
- **Abnahme:** `pip install -e ".[dev]"` läuft durch, `ruff check . && pytest` grün, `uvicorn flashcards.main:app` startet.

## Phase 1 – Datenmodell

- **Dateien:** `models.py`, `db.py`, `tests/conftest.py`, `tests/test_models.py`.
- **Modell:**
  - `Deck`: `id`, `name` (eindeutig), `created_at`.
  - `Card`: `id`, `deck_id` (FK, `ON DELETE CASCADE`), `front`, `back`, `box` (1–5, Standard 1, Check-Constraint), `due_date` (Standard heute), `last_reviewed_at` (optional), `created_at`.
  - SQLite-Fremdschlüssel per `PRAGMA foreign_keys=ON` aktivieren.
- **Tests:** neue Karte landet in Fach 1 und ist heute fällig; Deck löschen entfernt Karten; doppelter Deckname und `box` außerhalb 1–5 werden abgelehnt.
- **Abnahme:** Tests grün; `init_db()` erzeugt die Datei mit beiden Tabellen.

## Phase 2 – Leitner-Logik (reine Funktionen)

- **Dateien:** `leitner.py`, `tests/test_leitner.py`. Kein DB- und kein FastAPI-Import.
- **Funktionen:**
  - `BOX_INTERVALS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 14}`
  - `next_box(box, known) -> int`
  - `due_date_for(box, today) -> date`
  - `review(box, known, today) -> tuple[int, date]`
  - `is_due(due_date, today) -> bool`
- **Tests (parametrisiert):** gewusst 1→2 … 4→5, 5→5; nicht gewusst aus jedem Fach →1; Fälligkeit je Fach 0/1/3/7/14 Tage; `is_due` am Stichtag, davor, danach; ungültiges Fach wirft `ValueError`.
- **Abnahme:** alle fünf Intervalle und beide Antwortwege durch Tests belegt.

## Phase 3 – REST-API (Decks und Karten)

- **Dateien:** `schemas.py`, `services.py`, `routers/api.py`, `main.py` (Router einhängen), `tests/test_api_decks.py`, `tests/test_api_cards.py`.
- **Endpunkte:**
  - `GET/POST /api/decks`, `GET/PATCH/DELETE /api/decks/{id}`
  - `GET/POST /api/decks/{id}/cards`, `GET/PATCH/DELETE /api/cards/{id}`
- **Regeln:** Texte werden getrimmt, leere Werte ergeben 422; unbekannte ID 404; doppelter Deckname 409; `POST` 201, `DELETE` 204.
- **Tests:** je Endpunkt Erfolgsfall plus 404/409/422; Deck löschen entfernt Karten; `PATCH` einer Karte lässt `box`/`due_date` unverändert.
- **Abnahme:** Decks und Karten vollständig über `/docs` bedienbar.

## Phase 4 – HTML-Oberfläche (Decks und Karten)

- **Dateien:** `routers/pages.py`, `templates/base.html`, `decks.html`, `deck_detail.html`, `partials/` (Deckzeile, Kartenzeile, Bearbeitungsformulare), `static/htmx.min.js`, `static/pico.min.css`, `tests/test_pages.py`.
- **Seiten:** `/` Deckliste mit Anlegen; `/decks/{id}` Kartenliste mit Anlegen. Umbenennen, Bearbeiten und Löschen inline per HTMX (Partial-Austausch), Löschen mit Rückfrage. Texte auf Deutsch. Die Routen nutzen dieselben Funktionen aus `services.py` wie die API.
- **Tests:** Seiten liefern 200 und enthalten die Daten; Formular-POSTs legen an/ändern/löschen; HTMX-Anfragen liefern nur das Partial; Fehleingaben zeigen eine deutsche Meldung.
- **Abnahme:** Deck und Karten lassen sich im Browser ohne Seitenreload anlegen, ändern und löschen.

## Phase 5 – Features (je ein Commit)

### 5a Lernmodus

- **Dateien:** `deps.py`, Erweiterung `services.py`, `routers/api.py`, `routers/pages.py`, `templates/study.html`, `partials/study_card.html`, `tests/test_study.py`.
- **Ablauf:** `GET /decks/{id}/study` startet eine Sitzung mit Zeitstempel `started`, der in jedem Formular mitläuft. Angeboten werden Karten mit `due_date <= heute` und (`last_reviewed_at` leer oder `< started`) – so kommt jede Karte pro Sitzung genau einmal, ohne serverseitigen Sitzungsspeicher. Karte zeigt Vorderseite, "Aufdecken", dann "Gewusst" / "Nicht gewusst"; die Antwort ruft `leitner.review` auf, speichert `box`, `due_date`, `last_reviewed_at` und liefert die nächste Karte oder "Fertig für heute".
- **API:** `GET /api/decks/{id}/due`, `POST /api/cards/{id}/review` mit `{"known": bool}`.
- **Tests:** nur fällige Karten erscheinen; gewusst/nicht gewusst setzen Fach und Datum korrekt; nicht gewusste Karte erscheint in derselben Sitzung nicht erneut, in einer neuen schon; Reihenfolge; leeres Deck zeigt den Endzustand.
- **Abnahme:** ein Deck lässt sich komplett durchlernen, die Fächer stimmen danach mit der Regel überein.

### 5b Statistik

- **Dateien:** Erweiterung `services.py` (`deck_stats`), `schemas.py`, beide Router, `partials/stats.html`, `tests/test_stats.py`.
- **Inhalt:** Karten je Fach 1–5 (auch Nullen), Gesamtzahl, heute fällig. Anzeige auf der Deckseite, "heute fällig" zusätzlich in der Deckliste. API: `GET /api/decks/{id}/stats`.
- **Tests:** Zählung je Fach, leeres Deck, Fälligkeit am Stichtag und mit überfälligen Karten.
- **Abnahme:** Zahlen ändern sich nach einer Lernsitzung nachvollziehbar.

### 5c CSV-Import

- **Dateien:** `csv_import.py`, beide Router, `partials/import_result.html`, `tests/test_csv_import.py`.
- **Regeln:** Trennzeichen `;`, Anführungszeichen nach CSV-Standard, keine Kopfzeile. Dekodierung als UTF-8 (mit BOM), ersatzweise Windows-1252 (Excel). Leerzeilen werden ignoriert; Zeilen mit anderer Spaltenzahl oder leerer Seite gelten als fehlerhaft und werden mit Zeilennummer gemeldet, der Rest wird trotzdem importiert. Duplikate gegen das Deck und innerhalb der Datei werden übersprungen. Ergebnis: importiert / übersprungen / fehlerhaft.
- **API:** `POST /api/decks/{id}/import` (Datei-Upload); Formular auf der Deckseite.
- **Tests:** Parser als reine Funktion (gültig, Anführungszeichen mit `;` im Text, Leerzeilen, falsche Spaltenzahl, beide Kodierungen); Import mit Duplikaten; zweiter Import derselben Datei legt nichts an.
- **Abnahme:** eine aus Excel exportierte Datei mit Umlauten wird korrekt importiert, neue Karten liegen in Fach 1 und sind sofort fällig.

## Verifikation am Ende

1. `pip install -e ".[dev]"`, dann `ruff check . && pytest` – alles grün.
2. `uvicorn flashcards.main:app --reload`, im Browser: Deck anlegen und umbenennen, Karten anlegen/bearbeiten/löschen, CSV importieren, Lernsitzung durchspielen (gewusst und nicht gewusst), Statistik prüfen, Deck löschen.
3. `/docs` gegenprüfen: alle API-Endpunkte vorhanden und bedienbar.
