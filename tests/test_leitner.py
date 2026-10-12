from datetime import date, timedelta

import pytest

from lernkartei.leitner import BOX_INTERVALS, due_date_for, is_due, next_box, review

TODAY = date(2026, 3, 10)


def test_intervals_match_specification():
    assert BOX_INTERVALS == {1: 0, 2: 1, 3: 3, 4: 7, 5: 14}


@pytest.mark.parametrize(("box", "expected"), [(1, 2), (2, 3), (3, 4), (4, 5), (5, 5)])
def test_known_card_moves_one_box_up(box, expected):
    assert next_box(box, known=True) == expected


@pytest.mark.parametrize("box", [1, 2, 3, 4, 5])
def test_unknown_card_returns_to_first_box(box):
    assert next_box(box, known=False) == 1


@pytest.mark.parametrize(("box", "days"), [(1, 0), (2, 1), (3, 3), (4, 7), (5, 14)])
def test_due_date_depends_on_box(box, days):
    assert due_date_for(box, TODAY) == TODAY + timedelta(days=days)


@pytest.mark.parametrize(
    ("box", "new_box", "days"),
    [(1, 2, 1), (2, 3, 3), (3, 4, 7), (4, 5, 14), (5, 5, 14)],
)
def test_review_known_uses_interval_of_new_box(box, new_box, days):
    assert review(box, known=True, today=TODAY) == (new_box, TODAY + timedelta(days=days))


@pytest.mark.parametrize("box", [1, 2, 3, 4, 5])
def test_review_unknown_is_due_immediately(box):
    assert review(box, known=False, today=TODAY) == (1, TODAY)


def test_due_date_crosses_month_boundary():
    assert due_date_for(5, date(2026, 1, 25)) == date(2026, 2, 8)


@pytest.mark.parametrize(
    ("due_date", "expected"),
    [
        (TODAY - timedelta(days=1), True),
        (TODAY, True),
        (TODAY + timedelta(days=1), False),
    ],
)
def test_is_due(due_date, expected):
    assert is_due(due_date, TODAY) is expected


@pytest.mark.parametrize("box", [0, 6, -1])
def test_invalid_box_raises(box):
    with pytest.raises(ValueError):
        next_box(box, known=True)
    with pytest.raises(ValueError):
        due_date_for(box, TODAY)
    with pytest.raises(ValueError):
        review(box, known=False, today=TODAY)
