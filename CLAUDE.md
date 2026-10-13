# Flashcards

Karteikarten-Trainer mit Leitner-System als Webapp.

## Tech-Stack

- Python 3.12+ (Code bleibt 3.12-kompatibel, lokal läuft 3.14)
- FastAPI
- SQLModel mit SQLite
- Jinja2-Templates, HTMX, Pico.css (als Dateien in `src/flashcards/static/`, kein CDN)

## Projektstruktur

- src-Layout: Anwendungscode in `src/flashcards/`
- Tests in `tests/`
- Abhängigkeiten in `pyproject.toml`
- Planung und Fortschritt: `docs/PLAN.md`

## Architektur

- `leitner.py`: reine Funktionen, kein Import von FastAPI oder SQLModel
- `services.py`: Datenbanklogik, gemeinsam für API und HTML-Oberfläche
- `routers/api.py` liefert JSON unter `/api`, `routers/pages.py` liefert HTML und HTMX-Partials
- Datum und Uhrzeit nur über die Dependencies `get_today()` / `get_now()` aus `deps.py`, nie direkt `date.today()` oder `datetime.now()` in Logik oder Routen

## Befehle

- Installation: `pip install -e ".[dev]"`
- Linting: `ruff check .`
- Tests: `pytest`
- App starten: `uvicorn flashcards.main:app --reload`
- Vor jedem Commit: `ruff check . && pytest`

## Konventionen

- Code und Bezeichner auf Englisch
- Oberfläche (UI-Texte) und Kommentare auf Deutsch

## Arbeitsweise

- Kleine Schritte: ein Feature pro Auftrag, nicht mehrere Phasen am Stück
- Neue Logik testgetrieben: erst die Tests schreiben und ausführen (müssen rot sein), dann implementieren. Tests dabei nicht an den Code anpassen
- Nach jedem Feature anhalten: geänderte Dateien auflisten und auf mein Review warten. Erst nach meiner Freigabe committen
- Nichts über den Auftrag hinaus einbauen. Sinnvolle Ergänzungen (Limits, Schutzmechanismen, Sonderfälle) vorher vorschlagen, nicht selbst umsetzen
- Keine neuen Abhängigkeiten ohne Rückfrage
- Häkchen in `docs/PLAN.md` erst setzen, wenn ich das Feature im Browser geprüft habe
- Neue Features auf einem eigenen Branch (`feature/<name>`), nicht direkt auf `main`
