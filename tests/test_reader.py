"""Tests for the reader tool module (leggi_diario, lista_progetti)."""

from datetime import date
from unittest.mock import patch

from mcp_cronos.tools.reader import leggi_diario, lista_progetti


def test_reads_existing_file(sample_diary_it):
    """leggi_diario reads and parses an existing diary file."""
    with patch("mcp_cronos.tools.reader.get_today", return_value=date(2026, 4, 9)):
        result = leggi_diario(data="2026-04-09")

    assert result["riepilogo"]["files_trovati"] == 1
    giorni = result["giorni"]
    assert len(giorni) == 1
    assert giorni[0]["data"] == "2026-04-09"
    assert giorni[0]["num_entries"] >= 1


def test_file_not_found(tmp_diario):
    """leggi_diario collects missing day in date_mancanti and emits no stub in giorni."""
    with patch("mcp_cronos.tools.reader.get_today", return_value=date(2026, 4, 9)):
        result = leggi_diario(data="2026-04-09")

    assert result["giorni"] == []
    assert result["riepilogo"]["files_mancanti"] == 1
    assert result["riepilogo"]["date_mancanti"] == ["2026-04-09"]


def test_invalid_date_range(tmp_diario):
    """leggi_diario returns an error when start date is after end date."""
    result = leggi_diario(data_inizio="2026-04-10", data_fine="2026-04-09")
    assert "errore" in result


def test_reads_multiple_days(sample_diary_it, tmp_diario):
    """leggi_diario reads a range of dates; missing days land in date_mancanti."""
    with patch("mcp_cronos.tools.reader.get_today", return_value=date(2026, 4, 9)):
        result = leggi_diario(data_inizio="2026-04-08", data_fine="2026-04-09")

    assert result["periodo"]["giorni_totali"] == 2
    assert result["riepilogo"]["files_trovati"] == 1  # only 2026-04-09 exists
    assert result["riepilogo"]["files_mancanti"] == 1  # 2026-04-08 does not
    assert len(result["giorni"]) == 1
    assert "2026-04-08" in result["riepilogo"]["date_mancanti"]


def test_lista_progetti(sample_diary_it):
    """lista_progetti returns the projects found in the diary."""
    result = lista_progetti(data_inizio="2026-04-09", data_fine="2026-04-09")

    assert result["totale_progetti"] >= 1
    project_names = [p["nome"] for p in result["progetti"]]
    assert "MCP Cronos" in project_names


def test_lista_progetti_empty(tmp_diario):
    """lista_progetti returns zero projects when no diary files exist."""
    with patch("mcp_cronos.tools.reader.get_today", return_value=date(2026, 4, 9)):
        result = lista_progetti(ultimi_giorni=7)

    assert result["totale_progetti"] == 0


def test_leggi_diario_range_lists_missing_days_compactly(sample_diary_it):
    """leggi_diario emits only found days in giorni and collects missing dates in date_mancanti."""
    result = leggi_diario(data_inizio="2026-04-08", data_fine="2026-04-09")

    assert len(result["giorni"]) == 1
    assert result["giorni"][0]["data"] == "2026-04-09"
    assert result["riepilogo"]["files_trovati"] == 1
    assert result["riepilogo"]["files_mancanti"] == 1
    assert result["riepilogo"]["date_mancanti"] == ["2026-04-08"]
    assert all("esiste" not in g for g in result["giorni"])
