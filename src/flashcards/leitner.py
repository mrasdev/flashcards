"""Leitner rules as pure functions, without a database and without a clock."""

from datetime import date, timedelta

FIRST_BOX = 1
LAST_BOX = 5

# Days until the next due date per box.
BOX_INTERVALS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 14}


def _check_box(box: int) -> None:
    if box not in BOX_INTERVALS:
        raise ValueError(f"box must be between {FIRST_BOX} and {LAST_BOX}, got {box!r}")


def next_box(box: int, known: bool) -> int:
    _check_box(box)
    if not known:
        return FIRST_BOX
    return min(box + 1, LAST_BOX)


def due_date_for(box: int, today: date) -> date:
    _check_box(box)
    return today + timedelta(days=BOX_INTERVALS[box])


def review(box: int, known: bool, today: date) -> tuple[int, date]:
    new_box = next_box(box, known)
    return new_box, due_date_for(new_box, today)


def is_due(due_date: date, today: date) -> bool:
    return due_date <= today
