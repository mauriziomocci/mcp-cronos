"""
Tests for mcp_cronos.utils.dates.

Covers: format_standup_date, get_standup_title, get_file_path,
parse_date, get_date_range, ensure_directory_exists.
"""

from datetime import date

import pytest


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    """Reset the config singleton before and after every test."""
    from mcp_cronos.config import _reset_config

    _reset_config()
    yield
    _reset_config()


# ---------------------------------------------------------------------------
# get_standup_title — Italian default (no cronos.toml)
# ---------------------------------------------------------------------------


def test_get_standup_title_italian_default():
    """With no config file the default lang is 'it'; title must use Italian format."""
    from mcp_cronos.utils.dates import get_standup_title

    # file_date 2026-04-09 -> standup_date 2026-04-10
    result = get_standup_title(date(2026, 4, 9))
    assert result == "Per lo Stand-up - 10 Aprile 2026"


# ---------------------------------------------------------------------------
# get_standup_title — English config
# ---------------------------------------------------------------------------


def test_get_standup_title_english(config_toml_en):
    """With lang='en' in cronos.toml the title must use English format."""
    # Reload config so the fixture's cronos.toml is picked up
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.dates import get_standup_title

    _reset_config()

    # file_date 2026-04-09 -> standup_date 2026-04-10
    result = get_standup_title(date(2026, 4, 9))
    assert result == "For Stand-up - April 10, 2026"


# ---------------------------------------------------------------------------
# Path layout — new folder layout vs legacy single-file
# ---------------------------------------------------------------------------


def test_get_legacy_file_path(tmp_diario):
    """get_legacy_file_path always returns the single-file legacy path."""
    from mcp_cronos.utils.dates import get_legacy_file_path

    result = get_legacy_file_path(date(2026, 1, 21), diario_path=tmp_diario)
    assert result == tmp_diario / "2026" / "01" / "2026-01-21.md"


def test_get_day_folder_path(tmp_diario):
    """get_day_folder_path returns the per-day folder for the new layout."""
    from mcp_cronos.utils.dates import get_day_folder_path

    result = get_day_folder_path(date(2026, 5, 4), diario_path=tmp_diario)
    assert result == tmp_diario / "2026" / "05" / "2026-05-04"


def test_get_raw_path(tmp_diario):
    """get_raw_path returns <day_folder>/raw.md."""
    from mcp_cronos.utils.dates import get_raw_path

    result = get_raw_path(date(2026, 5, 4), diario_path=tmp_diario)
    assert result == tmp_diario / "2026" / "05" / "2026-05-04" / "raw.md"


def test_get_fine_giornata_path(tmp_diario):
    """get_fine_giornata_path returns <day_folder>/fine-giornata.md."""
    from mcp_cronos.utils.dates import get_fine_giornata_path

    result = get_fine_giornata_path(date(2026, 5, 4), diario_path=tmp_diario)
    assert result == tmp_diario / "2026" / "05" / "2026-05-04" / "fine-giornata.md"


def test_get_todo_path(tmp_diario):
    """get_todo_path returns <day_folder>/todo.md."""
    from mcp_cronos.utils.dates import get_todo_path

    result = get_todo_path(date(2026, 5, 4), diario_path=tmp_diario)
    assert result == tmp_diario / "2026" / "05" / "2026-05-04" / "todo.md"


# ---------------------------------------------------------------------------
# get_next_working_day
# ---------------------------------------------------------------------------


def test_get_next_working_day_monday_to_thursday():
    """Mon-Thu -> next day is just +1 (still a working day)."""
    from mcp_cronos.utils.dates import get_next_working_day

    # Mon 2026-05-04 -> Tue 2026-05-05
    assert get_next_working_day(date(2026, 5, 4)) == date(2026, 5, 5)
    # Thu 2026-05-07 -> Fri 2026-05-08
    assert get_next_working_day(date(2026, 5, 7)) == date(2026, 5, 8)


def test_get_next_working_day_friday_skips_to_monday():
    """Friday -> Monday of next week (+3 days)."""
    from mcp_cronos.utils.dates import get_next_working_day

    # Fri 2026-05-08 -> Mon 2026-05-11
    assert get_next_working_day(date(2026, 5, 8)) == date(2026, 5, 11)


def test_get_next_working_day_saturday_to_monday():
    """Saturday -> Monday (+2 days)."""
    from mcp_cronos.utils.dates import get_next_working_day

    # Sat 2026-05-09 -> Mon 2026-05-11
    assert get_next_working_day(date(2026, 5, 9)) == date(2026, 5, 11)


def test_get_next_working_day_sunday_to_monday():
    """Sunday -> Monday (+1 day)."""
    from mcp_cronos.utils.dates import get_next_working_day

    # Sun 2026-05-10 -> Mon 2026-05-11
    assert get_next_working_day(date(2026, 5, 10)) == date(2026, 5, 11)


def test_has_legacy_file_returns_false_when_missing(tmp_diario):
    """has_legacy_file is False when the single-file does not exist."""
    from mcp_cronos.utils.dates import has_legacy_file

    assert has_legacy_file(date(2026, 5, 4), diario_path=tmp_diario) is False


def test_has_legacy_file_returns_true_when_present(tmp_diario):
    """has_legacy_file is True after creating the legacy file."""
    from mcp_cronos.utils.dates import has_legacy_file

    legacy = tmp_diario / "2026" / "01" / "2026-01-21.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("legacy", encoding="utf-8")

    assert has_legacy_file(date(2026, 1, 21), diario_path=tmp_diario) is True


def test_resolve_raw_path_uses_legacy_when_present(tmp_diario):
    """resolve_raw_path returns the legacy path when the single-file exists."""
    from mcp_cronos.utils.dates import resolve_raw_path

    legacy = tmp_diario / "2026" / "01" / "2026-01-21.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("legacy", encoding="utf-8")

    result = resolve_raw_path(date(2026, 1, 21), diario_path=tmp_diario)
    assert result == legacy


def test_resolve_raw_path_uses_new_layout_when_no_legacy(tmp_diario):
    """resolve_raw_path returns raw.md inside the day folder when no legacy."""
    from mcp_cronos.utils.dates import resolve_raw_path

    result = resolve_raw_path(date(2026, 5, 4), diario_path=tmp_diario)
    assert result == tmp_diario / "2026" / "05" / "2026-05-04" / "raw.md"


def test_resolve_fine_giornata_path_uses_legacy_when_present(tmp_diario):
    """resolve_fine_giornata_path returns the legacy path when the single-file exists."""
    from mcp_cronos.utils.dates import resolve_fine_giornata_path

    legacy = tmp_diario / "2026" / "01" / "2026-01-21.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("legacy", encoding="utf-8")

    result = resolve_fine_giornata_path(date(2026, 1, 21), diario_path=tmp_diario)
    assert result == legacy


def test_resolve_fine_giornata_path_uses_new_layout_when_no_legacy(tmp_diario):
    """resolve_fine_giornata_path points to the new fine-giornata.md when no legacy."""
    from mcp_cronos.utils.dates import resolve_fine_giornata_path

    result = resolve_fine_giornata_path(date(2026, 5, 4), diario_path=tmp_diario)
    assert result == tmp_diario / "2026" / "05" / "2026-05-04" / "fine-giornata.md"


# ---------------------------------------------------------------------------
# get_file_path (backward-compat alias for resolve_raw_path)
# ---------------------------------------------------------------------------


def test_get_file_path_returns_legacy_when_present(tmp_diario):
    """get_file_path keeps using the legacy single-file when it exists."""
    from mcp_cronos.utils.dates import get_file_path

    legacy = tmp_diario / "2026" / "01" / "2026-01-21.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("legacy", encoding="utf-8")

    result = get_file_path(date(2026, 1, 21), diario_path=tmp_diario)
    assert result == legacy


def test_get_file_path_returns_new_raw_when_no_legacy(tmp_diario):
    """get_file_path falls back to <day_folder>/raw.md when no legacy file exists."""
    from mcp_cronos.utils.dates import get_file_path

    result = get_file_path(date(2026, 5, 4), diario_path=tmp_diario)
    expected = tmp_diario / "2026" / "05" / "2026-05-04" / "raw.md"
    assert result == expected


def test_get_file_path_uses_config_when_no_arg(tmp_diario):
    """get_file_path falls back to get_diario_path() when diario_path is None."""
    from mcp_cronos.utils.dates import get_file_path

    result = get_file_path(date(2026, 3, 5))
    expected = tmp_diario / "2026" / "03" / "2026-03-05" / "raw.md"
    assert result == expected


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------


def test_parse_date_valid():
    """parse_date must accept a valid YYYY-MM-DD string."""
    from mcp_cronos.utils.dates import parse_date

    assert parse_date("2026-04-09") == date(2026, 4, 9)


def test_parse_date_invalid_format():
    """parse_date must raise ValueError for a non-ISO date string."""
    from mcp_cronos.utils.dates import parse_date

    with pytest.raises(ValueError, match="Formato data non valido"):
        parse_date("09-04-2026")


def test_parse_date_invalid_value():
    """parse_date must raise ValueError for an impossible date."""
    from mcp_cronos.utils.dates import parse_date

    with pytest.raises(ValueError):
        parse_date("2026-13-01")


# ---------------------------------------------------------------------------
# get_date_range
# ---------------------------------------------------------------------------


def test_get_date_range_single_day():
    """When start == end get_date_range must return a list with exactly one date."""
    from mcp_cronos.utils.dates import get_date_range

    result = get_date_range(date(2026, 4, 9), date(2026, 4, 9))
    assert result == [date(2026, 4, 9)]


def test_get_date_range_multi_day():
    """get_date_range must return all dates between start and end inclusive."""
    from mcp_cronos.utils.dates import get_date_range

    result = get_date_range(date(2026, 4, 9), date(2026, 4, 11))
    assert result == [date(2026, 4, 9), date(2026, 4, 10), date(2026, 4, 11)]


def test_get_date_range_empty_when_start_after_end():
    """get_date_range must return an empty list when start is after end."""
    from mcp_cronos.utils.dates import get_date_range

    result = get_date_range(date(2026, 4, 11), date(2026, 4, 9))
    assert result == []


# ---------------------------------------------------------------------------
# ensure_directory_exists
# ---------------------------------------------------------------------------


def test_ensure_directory_exists_creates_parents(tmp_path):
    """ensure_directory_exists must create all missing parent directories."""
    from mcp_cronos.utils.dates import ensure_directory_exists

    target = tmp_path / "a" / "b" / "c" / "diary.md"
    ensure_directory_exists(target)
    assert target.parent.exists()
    assert target.parent.is_dir()


def test_get_next_working_day_skips_christmas_cluster(tmp_diario):
    """Thu 2026-12-24 -> Mon 2026-12-28 (skips Christmas, Santo Stefano, weekend)."""
    from mcp_cronos.utils.dates import get_next_working_day

    assert get_next_working_day(date(2026, 12, 24)) == date(2026, 12, 28)


def test_get_next_working_day_skips_easter_monday(tmp_diario):
    """Fri 2026-04-03 -> Tue 2026-04-07 (skips weekend and Easter Monday 04-06)."""
    from mcp_cronos.utils.dates import get_next_working_day

    assert get_next_working_day(date(2026, 4, 3)) == date(2026, 4, 7)


def test_get_next_working_day_skips_extra_holiday(tmp_diario):
    """With 2026-12-07 as an extra holiday: Fri 2026-12-04 -> Wed 2026-12-09
    (skips weekend, the configured 12-07, and Immacolata 12-08)."""
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n[cronos.calendar]\nextra_holidays = ["2026-12-07"]\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.dates import get_next_working_day

    _reset_config()
    assert get_next_working_day(date(2026, 12, 4)) == date(2026, 12, 9)


def test_get_previous_working_day_skips_christmas_cluster(tmp_diario):
    """Mon 2026-12-28 -> Thu 2026-12-24 (skips weekend, Santo Stefano, Christmas)."""
    from mcp_cronos.utils.dates import get_previous_working_day

    assert get_previous_working_day(date(2026, 12, 28)) == date(2026, 12, 24)


def test_get_previous_working_day_skips_extra_holiday(tmp_diario):
    """With 2026-12-07 as an extra holiday: Wed 2026-12-09 -> Fri 2026-12-04
    (skips Immacolata 12-08, the configured 12-07, and weekend)."""
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n[cronos.calendar]\nextra_holidays = ["2026-12-07"]\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.dates import get_previous_working_day

    _reset_config()
    assert get_previous_working_day(date(2026, 12, 9)) == date(2026, 12, 4)


def test_get_next_working_day_when_start_is_holiday(tmp_diario):
    """Strictly-after: starting from Christmas (Fri 2026-12-25) -> Mon 2026-12-28."""
    from mcp_cronos.utils.dates import get_next_working_day

    assert get_next_working_day(date(2026, 12, 25)) == date(2026, 12, 28)
