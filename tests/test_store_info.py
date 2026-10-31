from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from in_tune.tools.store_info import TZ, store_status


def at(*args):
    return datetime(*args, tzinfo=TZ)


def test_open_on_a_weekday_afternoon():
    status = store_status(at(2026, 10, 30, 15, 0))  # Friday
    assert status["open_now"] is True
    assert status["today"] == "09:00–18:00"
    assert status["next_opening"] is None


def test_saturday_closes_at_13_and_skips_the_finados_holiday():
    status = store_status(at(2026, 10, 31, 16, 50))  # Saturday afternoon
    assert status["open_now"] is False
    assert status["today"] == "09:00–13:00"
    # Sunday is closed and Monday 2026-11-02 is Finados.
    assert status["next_opening"] == "terça, 03/11/2026, 09:00"


def test_holiday_is_named():
    status = store_status(at(2026, 11, 2, 10, 0))
    assert status["today"] == "closed (Finados)"
    assert status["open_now"] is False


@pytest.mark.parametrize(
    ("moment", "expected_next"),
    [
        (at(2026, 11, 3, 7, 30), "terça, 03/11/2026, 09:00"),  # before opening, same day
        (at(2026, 11, 3, 18, 0), "quarta, 04/11/2026, 09:00"),  # closing time is closed
    ],
)
def test_next_opening(moment, expected_next):
    assert store_status(moment)["next_opening"] == expected_next


@pytest.mark.parametrize(
    ("moment", "is_open"),
    [
        (at(2026, 11, 3, 9, 0), True),  # opening minute
        (at(2026, 11, 3, 8, 59), False),
        (at(2026, 11, 7, 13, 0), False),  # Saturday closing time
        (at(2026, 11, 7, 12, 59), True),
        (at(2026, 11, 8, 11, 0), False),  # an ordinary Sunday
    ],
)
def test_opening_hour_boundaries(moment, is_open):
    assert store_status(moment)["open_now"] is is_open


def test_naive_time_is_read_as_campo_grande_time():
    assert store_status(datetime(2026, 11, 3, 9, 30))["now"].endswith("09:30")


def test_converts_other_timezones_to_campo_grande():
    # 14:30 in São Paulo (UTC−3) is 13:30 in Campo Grande (UTC−4): Saturday, closed.
    status = store_status(datetime(2026, 10, 31, 14, 30, tzinfo=ZoneInfo("America/Sao_Paulo")))
    assert status["now"].endswith("13:30")
    assert status["open_now"] is False
