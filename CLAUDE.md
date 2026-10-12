# Lernkartei

Karteikarten-Trainer mit Leitner-System als Webapp.

## Tech-Stack

- Python 3.12
- FastAPI
- SQLModel mit SQLite
- Jinja2-Templates, HTMX, Pico.css

## Projektstruktur

- src-Layout: Anwendungscode in `src/lernkartei/`
- Tests in `tests/`
- Abhängigkeiten in `pyproject.toml`

## Befehle

- Installation: `pip install -e ".[dev]"`
- Linting: `ruff check .`
- Tests: `pytest`
- Vor jedem Commit: `ruff check . && pytest`

## Konventionen

- Code und Bezeichner auf Englisch
- Oberfläche (UI-Texte) und Kommentare auf Deutsch

## Arbeitsweise

- Kleine Schritte: nach jedem abgeschlossenen Feature einen Commit vorschlagen
- Keine neuen Abhängigkeiten ohne Rückfrage
