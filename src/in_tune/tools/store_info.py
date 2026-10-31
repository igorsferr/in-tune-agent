"""Whether the store is open now, and when it opens next (policy §2, §7.1)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Campo_Grande")
WEEKDAYS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
# §2: Mon–Fri 09:00–18:00, Sat 09:00–13:00, closed on Sundays and holidays.
HOURS = {**{d: (time(9), time(18)) for d in range(5)}, 5: (time(9), time(13))}
# 2026 national holidays (and the next New Year), to be extended each year.
# State and municipal holidays are not in the data, so none are assumed.
HOLIDAYS = {
    date(2026, 1, 1): "Confraternização Universal",
    date(2026, 4, 3): "Paixão de Cristo",
    date(2026, 4, 21): "Tiradentes",
    date(2026, 5, 1): "Dia do Trabalho",
    date(2026, 9, 7): "Independência do Brasil",
    date(2026, 10, 12): "Nossa Senhora Aparecida",
    date(2026, 11, 2): "Finados",
    date(2026, 11, 15): "Proclamação da República",
    date(2026, 11, 20): "Dia Nacional de Zumbi e da Consciência Negra",
    date(2026, 12, 25): "Natal",
    date(2027, 1, 1): "Confraternização Universal",
}


def _hours(day: date) -> tuple[time, time] | None:
    return None if day in HOLIDAYS else HOURS.get(day.weekday())


def _label(day: date) -> str:
    return f"{WEEKDAYS[day.weekday()]}, {day.strftime('%d/%m/%Y')}"


def store_status(now: datetime | None = None) -> dict:
    now = now or datetime.now(TZ)
    # A time without a timezone is read as Campo Grande time, never the machine's.
    now = now.replace(tzinfo=TZ) if now.tzinfo is None else now.astimezone(TZ)
    today = now.date()
    hours = _hours(today)
    is_open = hours is not None and hours[0] <= now.time() < hours[1]

    next_opening = None
    for offset in range(0, 15):
        day = today + timedelta(days=offset)
        day_hours = _hours(day)
        if day_hours and (offset > 0 or now.time() < day_hours[0]):
            next_opening = f"{_label(day)}, {day_hours[0]:%H:%M}"
            break

    return {
        "now": f"{_label(today)}, {now:%H:%M}",
        "open_now": is_open,
        "today": f"{hours[0]:%H:%M}–{hours[1]:%H:%M}"
        if hours
        else f"closed ({HOLIDAYS.get(today, 'domingo')})",
        "next_opening": None if is_open else next_opening,
    }
