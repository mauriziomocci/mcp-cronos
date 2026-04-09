"""
Tests for mcp_cronos.utils.dates.

Covers: format_standup_date, get_standup_title, get_file_path,
parse_date, get_date_range, ensure_directory_exists.
"""

from datetime import date
from pathlib import Path

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
    from mcp_cronos.utils.dates import get_standup_title

    # Reload config so the fixture's cronos.toml is picked up
    from mcp_cronos.config import _reset_config

    _reset_config()

    # file_date 2026-04-09 -> standup_date 2026-04-10
    result = get_standup_title(date(2026, 4, 9))
    assert result == "For Stand-up - April 10, 2026"


# ---------------------------------------------------------------------------
# get_file_path
# ---------------------------------------------------------------------------


def test_get_file_path_format(tmp_diario):
    """get_file_path must return <diario>/<year>/<month>/<year>-<month>-<day>.md."""
    from mcp_cronos.utils.dates import get_file_path

    result = get_file_path(date(2026, 1, 21), diario_path=tmp_diario)
    expected = tmp_diario / "2026" / "01" / "2026-01-21.md"
    assert result == expected


def test_get_file_path_uses_config_when_no_arg(tmp_diario):
    """When diario_path is omitted, get_file_path must fall back to get_diario_path()."""
    from mcp_cronos.utils.dates import get_file_path

    result = get_file_path(date(2026, 3, 5))
    expected = tmp_diario / "2026" / "03" / "2026-03-05.md"
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
