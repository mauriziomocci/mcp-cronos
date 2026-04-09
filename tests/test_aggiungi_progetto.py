"""Tests for the aggiungi_progetto tool module."""

from datetime import date
from unittest.mock import patch

from mcp_cronos.tools.aggiungi_progetto import aggiungi_a_progetto


def test_creates_new_entry_if_no_file(tmp_diario):
    """aggiungi_a_progetto creates a new diary file with the entry when none exists."""
    with patch("mcp_cronos.tools.aggiungi_progetto.get_today", return_value=date(2026, 4, 9)):
        result = aggiungi_a_progetto(
            progetto="NewProject",
            titolo_fase="Initial setup",
            contenuto="Set up the project structure.",
        )

    assert result["successo"] is True
    assert result["modalita"] == "nuova_entry"
    assert result["progetto"] == "NewProject"

    from pathlib import Path

    content = Path(result["file"]).read_text(encoding="utf-8")
    assert "### NewProject - Initial setup" in content
    assert "Set up the project structure." in content
    assert "## Bloccanti" in content


def test_appends_to_existing_project(sample_diary_it):
    """aggiungi_a_progetto appends an H4 sub-section to an existing project entry."""
    with patch("mcp_cronos.tools.aggiungi_progetto.get_today", return_value=date(2026, 4, 9)):
        result = aggiungi_a_progetto(
            progetto="MCP Cronos",
            titolo_fase="Add i18n support",
            contenuto="Implemented language packs for IT and EN.",
        )

    assert result["successo"] is True
    assert result["modalita"] == "aggiunto_a_esistente"

    content = sample_diary_it.read_text(encoding="utf-8")
    assert "#### Add i18n support" in content
    assert "Implemented language packs for IT and EN." in content
    # Original content should be preserved
    assert "### MCP Cronos - Refactoring config system" in content


def test_creates_new_entry_for_unknown_project(sample_diary_it):
    """aggiungi_a_progetto creates a new entry when the project does not exist yet."""
    with patch("mcp_cronos.tools.aggiungi_progetto.get_today", return_value=date(2026, 4, 9)):
        result = aggiungi_a_progetto(
            progetto="BrandNew",
            titolo_fase="Spike investigation",
            contenuto="Investigated feasibility of the new approach.",
        )

    assert result["successo"] is True
    assert result["modalita"] == "nuova_entry"

    content = sample_diary_it.read_text(encoding="utf-8")
    assert "### BrandNew - Spike investigation" in content


def test_with_references(tmp_diario):
    """aggiungi_a_progetto includes references in the generated markdown."""
    with patch("mcp_cronos.tools.aggiungi_progetto.get_today", return_value=date(2026, 4, 9)):
        result = aggiungi_a_progetto(
            progetto="RefProject",
            titolo_fase="Deploy",
            contenuto="Deployed to production.",
            repository="my-repo",
            branch="main",
            jira_ticket="PROJ-42",
        )

    assert result["successo"] is True
    from pathlib import Path

    content = Path(result["file"]).read_text(encoding="utf-8")
    assert "**Riferimenti:**" in content
    assert "my-repo" in content
    assert "`main`" in content
    assert "PROJ-42" in content


def test_invalid_date(tmp_diario):
    """aggiungi_a_progetto returns an error for an invalid date."""
    result = aggiungi_a_progetto(
        progetto="Test",
        titolo_fase="Test",
        contenuto="Test",
        data="invalid",
    )

    assert "errore" in result
