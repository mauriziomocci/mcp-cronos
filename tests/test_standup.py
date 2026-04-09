"""Tests for the standup tool module."""

from datetime import date
from unittest.mock import patch

from mcp_cronos.tools.standup import _determina_contesto_temporale, genera_riassunto_standup


def test_returns_style_instructions(sample_diary_it):
    """genera_riassunto_standup returns style instructions loaded from the template."""
    with patch("mcp_cronos.tools.standup.get_today", return_value=date(2026, 4, 10)):
        result = genera_riassunto_standup(data="2026-04-09")

    assert "istruzioni_stile" in result
    assert "ISTRUZIONI" in result["istruzioni_stile"]
    assert result["num_entries"] >= 1


def test_no_entries_returns_error(tmp_diario):
    """genera_riassunto_standup returns an error when no entries exist."""
    with patch("mcp_cronos.tools.standup.get_today", return_value=date(2026, 4, 10)):
        result = genera_riassunto_standup(data="2026-04-09")

    assert "errore" in result
    assert "Nessuna entry" in result["errore"]


def test_returns_projects_list(sample_diary_it):
    """genera_riassunto_standup returns the list of projects found."""
    with patch("mcp_cronos.tools.standup.get_today", return_value=date(2026, 4, 10)):
        result = genera_riassunto_standup(data="2026-04-09")

    assert "progetti" in result
    assert "MCP Cronos" in result["progetti"]


def test_temporal_context_yesterday(tmp_diario):
    """_determina_contesto_temporale returns 'Ieri' for yesterday's date."""
    today = date(2026, 4, 10)
    yesterday = date(2026, 4, 9)
    context = _determina_contesto_temporale([yesterday], today)
    assert "Ieri" in context


def test_temporal_context_range(tmp_diario):
    """_determina_contesto_temporale returns a range description for multiple dates."""
    today = date(2026, 4, 10)
    dates = [date(2026, 4, 7), date(2026, 4, 8), date(2026, 4, 9)]
    context = _determina_contesto_temporale(dates, today)
    # Should contain "Dal" ... "al" from the temporal pack
    assert "7" in context
    assert "9" in context


def test_date_range_query(sample_diary_it):
    """genera_riassunto_standup supports date range queries."""
    result = genera_riassunto_standup(
        data_inizio="2026-04-09",
        data_fine="2026-04-09",
    )

    assert "entries" in result
    assert result["num_entries"] >= 1


def test_invalid_date_range(tmp_diario):
    """genera_riassunto_standup returns error when start > end."""
    result = genera_riassunto_standup(
        data_inizio="2026-04-10",
        data_fine="2026-04-09",
    )

    assert "errore" in result
