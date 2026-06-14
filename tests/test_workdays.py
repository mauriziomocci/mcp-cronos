"""Tests for mcp_cronos.utils.workdays (holiday and working-day helpers)."""

from datetime import date


def test_is_holiday_fixed_national(tmp_diario):
    from mcp_cronos.utils.workdays import is_holiday

    assert is_holiday(date(2026, 12, 25)) is True  # Natale


def test_is_holiday_easter_monday(tmp_diario):
    from mcp_cronos.utils.workdays import is_holiday

    assert is_holiday(date(2026, 4, 6)) is True  # Pasquetta 2026 (mobile)


def test_is_holiday_false_on_plain_weekday(tmp_diario):
    from mcp_cronos.utils.workdays import is_holiday

    assert is_holiday(date(2026, 5, 5)) is False


def test_is_holiday_extra_from_config(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n'
        '[cronos.calendar]\nextra_holidays = ["2026-07-20"]\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.workdays import is_holiday

    _reset_config()
    assert is_holiday(date(2026, 7, 20)) is True


def test_is_working_day(tmp_diario):
    from mcp_cronos.utils.workdays import is_working_day

    assert is_working_day(date(2026, 5, 5)) is True
    assert is_working_day(date(2026, 5, 9)) is False  # Saturday
    assert is_working_day(date(2026, 12, 25)) is False  # Christmas (Friday)


def test_invalid_country_falls_back_without_raising(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n[cronos.calendar]\ncountry = "ZZ"\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.workdays import is_holiday

    _reset_config()
    assert is_holiday(date(2026, 12, 25)) is False
