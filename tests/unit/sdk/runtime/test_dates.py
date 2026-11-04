"""Data de referência: dia útil anterior (segunda → sexta)."""

from datetime import UTC, date, datetime

import pytest

from labdata.sdk.runtime.dates import previous_business_day, reference_date


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 11, 2), date(2026, 10, 30)),  # segunda → sexta
        (date(2026, 11, 3), date(2026, 11, 2)),  # terça → segunda
        (date(2026, 11, 7), date(2026, 11, 6)),  # sábado → sexta
        (date(2026, 11, 8), date(2026, 11, 6)),  # domingo → sexta
    ],
)
def test_previous_business_day(today, expected):
    assert previous_business_day(today) == expected


def test_uses_the_sao_paulo_timezone():
    # 02h UTC de terça ainda é segunda em Brasília: o dia útil anterior é sexta
    now = datetime(2026, 11, 3, 2, 0, tzinfo=UTC)
    assert reference_date("previous_business_day", timezone="America/Sao_Paulo", now=now) == date(2026, 10, 30)


def test_unknown_rule():
    with pytest.raises(ValueError):
        reference_date("holiday", timezone="America/Sao_Paulo")
