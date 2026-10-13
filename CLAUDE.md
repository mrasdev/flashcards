# Flashcards

Flashcard trainer using the Leitner system as a web app.

## Tech stack

- Python 3.12+ (code stays 3.12-compatible, 3.14 runs locally)
- HTMX and Pico.css as files in `src/flashcards/static/`, no CDN

## Project structure

- Planning and progress: `docs/PLAN.md`

## Architecture

- `leitner.py`: pure functions, no import of FastAPI or SQLModel
- `services.py`: database logic, shared by the API and the HTML interface
- `routers/api.py` serves JSON under `/api`, `routers/pages.py` serves HTML and HTMX partials
- Date and time only through the dependencies `get_today()` / `get_now()` from `deps.py`, never `date.today()` or `datetime.now()` directly in logic or routes

## Commands

- Before every commit: `ruff check . && pytest`

## Conventions

- Code, identifiers, UI texts, comments and documentation in English

## Workflow

- Small steps: one feature per task, not several phases at once
- New logic test-driven: write and run the tests first (they must fail), then implement. Do not adapt the tests to the code
- Stop after every feature: list the changed files and wait for my review. Commit only after my approval
- Build nothing beyond the task. Propose useful additions (limits, safeguards, edge cases) first, do not implement them unasked
- No new dependencies without asking
- Only tick boxes in `docs/PLAN.md` once I have checked the feature in the browser
- New features on their own branch (`feature/<name>`), not directly on `main`
