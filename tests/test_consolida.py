"""Tests for the consolida tool module."""

from datetime import date
from unittest.mock import patch

from mcp_cronos.tools.consolida import consolida_diario


def test_returns_instructions(sample_diary_it):
    """consolida_diario returns consolidation instructions and file content."""
    with patch("mcp_cronos.tools.consolida.get_today", return_value=date(2026, 4, 9)):
        result = consolida_diario()

    assert "istruzioni" in result
    assert "ISTRUZIONI" in result["istruzioni"]
    assert "contenuto_completo" in result
    assert result["data"] == "2026-04-09"
    assert "analisi" in result


def test_file_not_found(tmp_diario):
    """consolida_diario returns an error when the diary file does not exist."""
    with patch("mcp_cronos.tools.consolida.get_today", return_value=date(2026, 4, 9)):
        result = consolida_diario()

    assert "errore" in result
    assert "non trovato" in result["errore"]


def test_empty_file(tmp_diario):
    """consolida_diario returns an error for an empty diary file."""
    month_dir = tmp_diario / "2026" / "04"
    month_dir.mkdir(parents=True, exist_ok=True)
    diary_file = month_dir / "2026-04-09.md"
    diary_file.write_text("", encoding="utf-8")

    with patch("mcp_cronos.tools.consolida.get_today", return_value=date(2026, 4, 9)):
        result = consolida_diario()

    assert "errore" in result
    assert "vuoto" in result["errore"].lower() or "vuoto" in result["errore"]


def test_detects_duplicate_projects(tmp_diario):
    """consolida_diario detects projects with multiple H3 sections."""
    month_dir = tmp_diario / "2026" / "04"
    month_dir.mkdir(parents=True, exist_ok=True)
    diary_file = month_dir / "2026-04-09.md"
    diary_file.write_text(
        "# Title\n\n"
        "## Cosa ho fatto ieri\n\n"
        "### ProjectA - Task 1\n\nDid task 1.\n\n---\n\n"
        "### ProjectA - Task 2\n\nDid task 2.\n\n---\n\n"
        "### ProjectB - Task 3\n\nDid task 3.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )

    with patch("mcp_cronos.tools.consolida.get_today", return_value=date(2026, 4, 9)):
        result = consolida_diario()

    assert result["analisi"]["progetti_con_entry_multiple"] is not None
    assert "ProjectA" in result["analisi"]["progetti_con_entry_multiple"]


def test_template_contains_config_sections(sample_diary_it):
    """The consolidation instructions reference the configured section names."""
    with patch("mcp_cronos.tools.consolida.get_today", return_value=date(2026, 4, 9)):
        result = consolida_diario()

    instructions = result["istruzioni"]
    assert "Bloccanti" in instructions
