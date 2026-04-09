"""Tests for the settimana tool module (riassunto_settimana)."""

from datetime import date
from unittest.mock import patch

from mcp_cronos.tools.settimana import riassunto_settimana


def test_returns_week_range(sample_diary_it):
    """riassunto_settimana returns the correct Monday-Friday range."""
    with patch("mcp_cronos.tools.settimana.get_today", return_value=date(2026, 4, 9)):
        result = riassunto_settimana()

    # 2026-04-09 is a Thursday; Monday = 2026-04-06, Friday = 2026-04-10
    assert result["settimana"]["da"] == "2026-04-06"
    assert result["settimana"]["a"] == "2026-04-10"
    assert result["totale_progetti"] >= 1


def test_empty_week(tmp_diario):
    """riassunto_settimana returns zero projects for a week with no diary files."""
    with patch("mcp_cronos.tools.settimana.get_today", return_value=date(2026, 4, 9)):
        result = riassunto_settimana()

    assert result["giorni_lavorati"] == 0
    assert result["totale_progetti"] == 0
    assert result["progetti"] == []


def test_returns_project_details(sample_diary_it):
    """riassunto_settimana includes project details with entries."""
    with patch("mcp_cronos.tools.settimana.get_today", return_value=date(2026, 4, 9)):
        result = riassunto_settimana()

    assert len(result["progetti"]) >= 1
    project = result["progetti"][0]
    assert "progetto" in project
    assert "giorni" in project
    assert "entries" in project
    assert project["giorni"] >= 1


def test_specific_date(sample_diary_it):
    """riassunto_settimana accepts a specific date parameter."""
    result = riassunto_settimana(data="2026-04-09")

    assert result["settimana"]["da"] == "2026-04-06"
    assert result["totale_progetti"] >= 1


def test_invalid_date(tmp_diario):
    """riassunto_settimana returns an error for an invalid date."""
    result = riassunto_settimana(data="not-a-date")
    assert "errore" in result
