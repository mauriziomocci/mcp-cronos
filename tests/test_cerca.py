"""Tests for the cerca tool module (cerca_nel_diario)."""

from datetime import date
from unittest.mock import patch

from mcp_cronos.tools.cerca import cerca_nel_diario


def test_finds_match(sample_diary_it):
    """cerca_nel_diario finds entries matching the query."""
    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 4, 9)):
        result = cerca_nel_diario(
            query="config",
            data_inizio="2026-04-09",
            data_fine="2026-04-09",
        )

    assert result["totale_risultati"] >= 1
    assert result["risultati"][0]["progetto"] == "MCP Cronos"


def test_no_match(sample_diary_it):
    """cerca_nel_diario returns zero results when nothing matches."""
    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 4, 9)):
        result = cerca_nel_diario(
            query="xyznonexistent",
            data_inizio="2026-04-09",
            data_fine="2026-04-09",
        )

    assert result["totale_risultati"] == 0


def test_invalid_regex(tmp_diario):
    """cerca_nel_diario returns an error for an invalid regex pattern."""
    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 4, 9)):
        result = cerca_nel_diario(query="[invalid")

    assert "errore" in result
    assert "regex" in result["errore"].lower()


def test_case_insensitive(sample_diary_it):
    """cerca_nel_diario performs case-insensitive searches."""
    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 4, 9)):
        result = cerca_nel_diario(
            query="CONFIG",
            data_inizio="2026-04-09",
            data_fine="2026-04-09",
        )

    assert result["totale_risultati"] >= 1


def test_no_files_in_range(tmp_diario):
    """cerca_nel_diario returns zero results when no files exist in the range."""
    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 4, 9)):
        result = cerca_nel_diario(
            query="anything",
            data_inizio="2026-04-01",
            data_fine="2026-04-09",
        )

    assert result["totale_risultati"] == 0
    assert result["files_cercati"] == 0
