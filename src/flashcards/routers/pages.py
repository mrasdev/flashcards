from datetime import date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from flashcards import csv_import, services
from flashcards.deps import CardDep, DeckDep, NowDep, SessionDep, TodayDep

router = APIRouter(default_response_class=HTMLResponse, include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

FormText = Annotated[str, Form()]

ERROR_DECK_NAME_EMPTY = "Bitte einen Namen eingeben."
ERROR_DECK_NAME_TAKEN = "Ein Deck mit diesem Namen existiert bereits."
ERROR_CARD_TEXT_EMPTY = "Vorder- und Rückseite dürfen nicht leer sein."
ERROR_IMPORT_NO_FILE = "Bitte eine CSV-Datei auswählen."
ERROR_IMPORT_TOO_LARGE = "Die Datei ist größer als 1 MB."


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _render(request: Request, page: str, partial: str, context: dict, failed: bool = False):
    # HTMX bekommt nur das Partial (immer 200, sonst tauscht es nichts aus),
    # ein normaler Seitenaufruf die ganze Seite.
    if _is_htmx(request):
        return templates.TemplateResponse(request, partial, context)
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT if failed else status.HTTP_200_OK
    return templates.TemplateResponse(request, page, context, status_code=status_code)


def _deck_context(session, today: date, error: str | None = None, name: str = "") -> dict:
    return {
        "decks": services.list_decks(session),
        "due_counts": services.due_counts(session, today),
        "error": error,
        "name": name,
    }


def _deck_row_context(session, deck, today: date) -> dict:
    return {"deck": deck, "due_counts": services.due_counts(session, today)}


def _card_context(
    session,
    deck,
    today: date,
    error: str | None = None,
    front: str = "",
    back: str = "",
    import_result: csv_import.ImportResult | None = None,
    import_error: str | None = None,
) -> dict:
    return {
        "deck": deck,
        "cards": services.list_cards(session, deck),
        "stats": services.deck_stats(session, deck, today),
        "error": error,
        "front": front,
        "back": back,
        "import_result": import_result,
        "import_error": import_error,
    }


@router.get("/")
def deck_list(request: Request, session: SessionDep, today: TodayDep):
    return templates.TemplateResponse(request, "decks.html", _deck_context(session, today))


@router.post("/decks")
def create_deck(request: Request, session: SessionDep, today: TodayDep, name: FormText = ""):
    error = None
    try:
        services.create_deck(session, name)
    except services.EmptyTextError:
        error = ERROR_DECK_NAME_EMPTY
    except services.DuplicateDeckNameError:
        error = ERROR_DECK_NAME_TAKEN
    if error is None and not _is_htmx(request):
        return RedirectResponse("/", status.HTTP_303_SEE_OTHER)
    context = _deck_context(session, today, error, name if error else "")
    return _render(request, "decks.html", "partials/deck_section.html", context, bool(error))


@router.get("/decks/{deck_id}")
def deck_detail(request: Request, deck: DeckDep, session: SessionDep, today: TodayDep):
    context = _card_context(session, deck, today)
    return templates.TemplateResponse(request, "deck_detail.html", context)


@router.get("/decks/{deck_id}/row")
def deck_row(request: Request, deck: DeckDep, session: SessionDep, today: TodayDep):
    context = _deck_row_context(session, deck, today)
    return templates.TemplateResponse(request, "partials/deck_row.html", context)


@router.get("/decks/{deck_id}/edit")
def deck_edit_form(request: Request, deck: DeckDep):
    context = {"deck": deck, "name": deck.name, "error": None}
    return templates.TemplateResponse(request, "partials/deck_row_edit.html", context)


@router.put("/decks/{deck_id}")
def rename_deck(
    request: Request, deck: DeckDep, session: SessionDep, today: TodayDep, name: FormText = ""
):
    try:
        services.rename_deck(session, deck, name)
    except services.EmptyTextError:
        error = ERROR_DECK_NAME_EMPTY
    except services.DuplicateDeckNameError:
        error = ERROR_DECK_NAME_TAKEN
    else:
        context = _deck_row_context(session, deck, today)
        return templates.TemplateResponse(request, "partials/deck_row.html", context)
    context = {"deck": deck, "name": name, "error": error}
    return templates.TemplateResponse(request, "partials/deck_row_edit.html", context)


@router.delete("/decks/{deck_id}")
def delete_deck(request: Request, deck: DeckDep, session: SessionDep, today: TodayDep):
    services.delete_deck(session, deck)
    return templates.TemplateResponse(
        request, "partials/deck_section.html", _deck_context(session, today)
    )


@router.post("/decks/{deck_id}/cards")
def create_card(
    request: Request,
    deck: DeckDep,
    session: SessionDep,
    today: TodayDep,
    front: FormText = "",
    back: FormText = "",
):
    error = None
    try:
        services.create_card(session, deck, front, back, today)
    except services.EmptyTextError:
        error = ERROR_CARD_TEXT_EMPTY
    if error is None and not _is_htmx(request):
        return RedirectResponse(f"/decks/{deck.id}", status.HTTP_303_SEE_OTHER)
    context = (
        _card_context(session, deck, today, error, front, back)
        if error
        else _card_context(session, deck, today)
    )
    return _render(
        request, "deck_detail.html", "partials/card_section.html", context, bool(error)
    )


@router.post("/decks/{deck_id}/import")
def import_cards(
    request: Request,
    deck: DeckDep,
    session: SessionDep,
    today: TodayDep,
    file: UploadFile | None = None,
):
    result = error = None
    if file is None or not file.filename:
        error = ERROR_IMPORT_NO_FILE
    else:
        data = file.file.read(csv_import.MAX_UPLOAD_BYTES + 1)
        if len(data) > csv_import.MAX_UPLOAD_BYTES:
            error = ERROR_IMPORT_TOO_LARGE
        else:
            result = csv_import.import_csv(session, deck, data, today)
    context = _card_context(session, deck, today, import_result=result, import_error=error)
    return _render(
        request, "deck_detail.html", "partials/card_section.html", context, bool(error)
    )


@router.get("/cards/{card_id}/row")
def card_row(request: Request, card: CardDep):
    return templates.TemplateResponse(request, "partials/card_row.html", {"card": card})


@router.get("/cards/{card_id}/edit")
def card_edit_form(request: Request, card: CardDep):
    context = {"card": card, "front": card.front, "back": card.back, "error": None}
    return templates.TemplateResponse(request, "partials/card_row_edit.html", context)


@router.put("/cards/{card_id}")
def update_card(
    request: Request,
    card: CardDep,
    session: SessionDep,
    front: FormText = "",
    back: FormText = "",
):
    try:
        services.update_card(session, card, front=front, back=back)
    except services.EmptyTextError:
        context = {"card": card, "front": front, "back": back, "error": ERROR_CARD_TEXT_EMPTY}
        return templates.TemplateResponse(request, "partials/card_row_edit.html", context)
    return templates.TemplateResponse(request, "partials/card_row.html", {"card": card})


@router.delete("/cards/{card_id}")
def delete_card(request: Request, card: CardDep, session: SessionDep, today: TodayDep):
    deck = card.deck
    services.delete_card(session, card)
    return templates.TemplateResponse(
        request, "partials/card_section.html", _card_context(session, deck, today)
    )


def _study_context(session, deck, today: date, started: datetime) -> dict:
    pending = services.due_cards(session, deck, today, started)
    return {
        "deck": deck,
        "started": started,
        "card": pending[0] if pending else None,
        "remaining": len(pending),
        # Nicht gewusste Karten sind weiter fällig, kommen aber erst in der nächsten Sitzung.
        "postponed": 0 if pending else len(services.due_cards(session, deck, today)),
    }


@router.get("/decks/{deck_id}/study")
def study(request: Request, deck: DeckDep, session: SessionDep, today: TodayDep, now: NowDep):
    # Jeder Aufruf beginnt eine neue Sitzung; ihr Startzeitpunkt läuft im Formular mit.
    context = _study_context(session, deck, today, now)
    return templates.TemplateResponse(request, "study.html", context)


@router.post("/cards/{card_id}/answer")
def answer_card(
    request: Request,
    card: CardDep,
    session: SessionDep,
    today: TodayDep,
    now: NowDep,
    known: Annotated[bool, Form()],
    started: Annotated[datetime, Form()],
):
    # Doppelt abgeschickte Antworten zählen nicht noch einmal.
    if services.is_pending(card, today, started):
        services.review_card(session, card, known, today, now)
    context = _study_context(session, card.deck, today, started)
    return _render(request, "study.html", "partials/study_card.html", context)
