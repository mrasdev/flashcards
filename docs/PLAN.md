# Flashcards implementation plan

Flashcard trainer based on the Leitner system as a web app (FastAPI, SQLModel/SQLite, Jinja2, HTMX, Pico.css) with decks, cards, study mode, statistics and CSV import. Each phase ends with `ruff check . && pytest` and a commit.

## Progress

- [x] Phase 0 – Project skeleton
- [x] Phase 1 – Data model
- [x] Phase 2 – Leitner logic (pure functions)
- [x] Phase 3 – REST API (decks and cards)
- [x] Phase 4 – HTML interface (decks and cards)
- [x] Phase 5a – Study mode
- [x] Phase 5b – Statistics
- [x] Phase 5c – CSV import
- [x] Final verification
- [x] Keyboard control in study mode

## Decisions

- **Packages:** in addition to the stack, `uvicorn`, `python-multipart` (runtime) and `httpx` (dev).
- **Due dates:** calendar days. A card stores a `due_date` (date); a card is due when `due_date <= today`.
- **Study session:** each card appears only once per session. Cards not known only come back the next time study mode is started.
- **CSV:** no header row, duplicates (same front and back in the deck) are skipped.
- **Keyboard control without an off switch:** the single-key shortcuts K/N in study mode cannot be turned off or remapped, as WCAG 2.1.4 would require. A deliberate decision: single-user app, no conformance requirement, and K/N only act on a revealed card.

## Assumptions

- Single user, no login.
- No migration tool: tables are created with `SQLModel.metadata.create_all` on startup. The DB path comes from the environment variable `FLASHCARDS_DB`, default `flashcards.db` (in `.gitignore`).
- Deck names are unique; a duplicate name results in 409 or a form error.
- Deleting a deck also deletes its cards (confirmation via `hx-confirm`).
- Editing a card does not change its box or due date.
- A known card in box 5 stays in box 5 and is due again in 14 days.
- Order in study mode: lowest box first, then oldest due date, then ID.
- HTMX and Pico.css are stored as files in `src/flashcards/static/` (no CDN, works offline).
- "Today" comes from a FastAPI dependency `get_today()` that tests override – no time-mocking library needed.

## Target structure

```
pyproject.toml
.gitignore
src/flashcards/
  __init__.py
  main.py            # app, routers, static files, lifespan (init_db)
  db.py              # engine, get_session, init_db
  models.py          # Deck, Card
  schemas.py         # input/output models of the API
  leitner.py         # pure functions
  services.py        # DB operations shared by API and HTML
  csv_import.py      # parser (pure) + import
  deps.py            # get_today
  routers/api.py     # JSON under /api
  routers/pages.py   # HTML/HTMX
  templates/         # base.html, pages, partials/
  static/            # htmx.min.js, pico.min.css
tests/
  conftest.py        # in-memory SQLite (StaticPool), session, TestClient, fixed date
  test_models.py, test_leitner.py, test_api_decks.py, test_api_cards.py,
  test_pages.py, test_study.py, test_stats.py, test_csv_import.py
```

## Phase 0 – Project skeleton

- **Files:** `pyproject.toml` (setuptools, src layout, dependencies, `[dev]` extra, ruff and pytest configuration), `.gitignore`, `src/flashcards/__init__.py`, `main.py` with `GET /health`, `tests/test_health.py`.
- **Tests:** `/health` returns 200.
- **Acceptance:** `pip install -e ".[dev]"` completes, `ruff check . && pytest` passes, `uvicorn flashcards.main:app` starts.

## Phase 1 – Data model

- **Files:** `models.py`, `db.py`, `tests/conftest.py`, `tests/test_models.py`.
- **Model:**
  - `Deck`: `id`, `name` (unique), `created_at`.
  - `Card`: `id`, `deck_id` (FK, `ON DELETE CASCADE`), `front`, `back`, `box` (1–5, default 1, check constraint), `due_date` (default today), `last_reviewed_at` (optional), `created_at`.
  - Enable SQLite foreign keys with `PRAGMA foreign_keys=ON`.
- **Tests:** a new card lands in box 1 and is due today; deleting a deck removes its cards; a duplicate deck name and a `box` outside 1–5 are rejected.
- **Acceptance:** tests pass; `init_db()` creates the file with both tables.

## Phase 2 – Leitner logic (pure functions)

- **Files:** `leitner.py`, `tests/test_leitner.py`. No DB and no FastAPI import.
- **Functions:**
  - `BOX_INTERVALS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 14}`
  - `next_box(box, known) -> int`
  - `due_date_for(box, today) -> date`
  - `review(box, known, today) -> tuple[int, date]`
  - `is_due(due_date, today) -> bool`
- **Tests (parametrized):** known 1→2 … 4→5, 5→5; not known from any box →1; due date per box 0/1/3/7/14 days; `is_due` on the due date, before and after; an invalid box raises `ValueError`.
- **Acceptance:** all five intervals and both answer paths are covered by tests.

## Phase 3 – REST API (decks and cards)

- **Files:** `schemas.py`, `services.py`, `routers/api.py`, `main.py` (include the router), `tests/test_api_decks.py`, `tests/test_api_cards.py`.
- **Endpoints:**
  - `GET/POST /api/decks`, `GET/PATCH/DELETE /api/decks/{id}`
  - `GET/POST /api/decks/{id}/cards`, `GET/PATCH/DELETE /api/cards/{id}`
- **Rules:** texts are trimmed, empty values result in 422; unknown ID 404; duplicate deck name 409; `POST` 201, `DELETE` 204.
- **Tests:** a success case plus 404/409/422 per endpoint; deleting a deck removes its cards; `PATCH` on a card leaves `box`/`due_date` unchanged.
- **Acceptance:** decks and cards can be fully operated through `/docs`.

## Phase 4 – HTML interface (decks and cards)

- **Files:** `routers/pages.py`, `templates/base.html`, `decks.html`, `deck_detail.html`, `partials/` (deck row, card row, edit forms), `static/htmx.min.js`, `static/pico.min.css`, `tests/test_pages.py`.
- **Pages:** `/` deck list with creation; `/decks/{id}` card list with creation. Renaming, editing and deleting happen inline via HTMX (partial swap), deleting with confirmation. The routes use the same functions from `services.py` as the API.
- **Tests:** pages return 200 and contain the data; form POSTs create/change/delete; HTMX requests return only the partial; invalid input shows an error message.
- **Acceptance:** a deck and cards can be created, changed and deleted in the browser without a page reload.

## Phase 5 – Features (one commit each)

### 5a Study mode

- **Files:** `deps.py`, extension of `services.py`, `routers/api.py`, `routers/pages.py`, `templates/study.html`, `partials/study_card.html`, `tests/test_study.py`.
- **Flow:** `GET /decks/{id}/study` starts a session with a timestamp `started` that travels along in every form. Cards with `due_date <= today` and (`last_reviewed_at` empty or `< started`) are offered – this way each card comes up exactly once per session, without server-side session storage. A card shows the front, "Reveal", then "Known" / "Not known"; the answer calls `leitner.review`, stores `box`, `due_date`, `last_reviewed_at` and returns the next card or "Done for today".
- **API:** `GET /api/decks/{id}/due`, `POST /api/cards/{id}/review` with `{"known": bool}`.
- **Tests:** only due cards appear; known/not known set box and date correctly; a card not known does not appear again in the same session but does in a new one; order; an empty deck shows the end state.
- **Acceptance:** a deck can be studied completely, and the boxes match the rule afterwards.

### 5b Statistics

- **Files:** extension of `services.py` (`deck_stats`), `schemas.py`, both routers, `partials/stats.html`, `tests/test_stats.py`.
- **Content:** cards per box 1–5 (including zeros), total, due today. Shown on the deck page, "due today" also in the deck list. API: `GET /api/decks/{id}/stats`.
- **Tests:** count per box, empty deck, due on the due date and with overdue cards.
- **Acceptance:** the numbers change in a comprehensible way after a study session.

### 5c CSV import

- **Files:** `csv_import.py`, both routers, `partials/import_result.html`, `tests/test_csv_import.py`.
- **Rules:** delimiter `;`, quoting according to the CSV standard, no header row. Decoded as UTF-8 (with BOM), falling back to Windows-1252 (Excel). Blank lines are ignored; lines with a different number of columns or an empty side count as invalid and are reported with their line number, the rest is imported anyway. Duplicates against the deck and within the file are skipped. Result: imported / skipped / invalid.
- **API:** `POST /api/decks/{id}/import` (file upload); form on the deck page.
- **Tests:** parser as a pure function (valid, quotes with `;` in the text, blank lines, wrong number of columns, both encodings); import with duplicates; a second import of the same file creates nothing.
- **Acceptance:** a file exported from Excel with umlauts is imported correctly, new cards are in box 1 and due immediately.

## Final verification

1. `pip install -e ".[dev]"`, then `ruff check . && pytest` – everything passes.
2. `uvicorn flashcards.main:app --reload`, in the browser: create and rename a deck, create/edit/delete cards, import a CSV, play through a study session (known and not known), check the statistics, delete the deck.
3. Cross-check `/docs`: all API endpoints are present and usable.
