"""Cálculo da data de referência de uma execução."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

RULES = ("previous_business_day", "yesterday", "today")


def previous_business_day(today: date) -> date:
    """Dia útil anterior, considerando só fins de semana (segunda → sexta).

    Feriados não entram aqui: num feriado a fonte responde sem dado, e a execução termina sem dado novo.
    """
    d = today - timedelta(days=1)
    while d.weekday() >= 5:  # 5 = sábado, 6 = domingo
        d -= timedelta(days=1)
    return d


def reference_date(rule: str, *, timezone: str, now: datetime | None = None) -> date:
    today = (now or datetime.now(ZoneInfo(timezone))).astimezone(ZoneInfo(timezone)).date()
    if rule == "previous_business_day":
        return previous_business_day(today)
    if rule == "yesterday":
        return today - timedelta(days=1)
    if rule == "today":
        return today
    raise ValueError(f"regra de data de referência desconhecida: {rule!r}")
