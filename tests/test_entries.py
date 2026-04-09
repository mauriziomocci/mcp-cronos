"""Tests for the entries tool module (aggiungi_entry, imposta_bloccanti)."""

from datetime import date
from unittest.mock import patch

from mcp_cronos.tools.entries import aggiungi_entry, imposta_bloccanti


def test_creates_new_file(tmp_diario):
    """aggiungi_entry creates a new diary file when none exists."""
    with patch("mcp_cronos.tools.entries.get_today", return_value=date(2026, 4, 9)):
        result = aggiungi_entry(
            progetto="TestProject",
            descrizione="Initial setup",
            paragrafo_intro="Set up the project from scratch.",
        )

    assert result["successo"] is True
    assert "2026-04-09" in result["file"]
    assert result["progetto"] == "TestProject"

    from pathlib import Path

    content = Path(result["file"]).read_text(encoding="utf-8")
    assert "### TestProject - Initial setup" in content
    assert "Set up the project from scratch." in content
    assert "## Bloccanti" in content


def test_appends_to_existing_file(sample_diary_it):
    """aggiungi_entry appends an entry to an existing diary file."""
    with patch("mcp_cronos.tools.entries.get_today", return_value=date(2026, 4, 9)):
        result = aggiungi_entry(
            progetto="NewProject",
            descrizione="New feature",
            paragrafo_intro="Added a new feature.",
        )

    assert result["successo"] is True
    content = sample_diary_it.read_text(encoding="utf-8")
    assert "### NewProject - New feature" in content
    # Original entries should still be there
    assert "### MCP Cronos - Refactoring config system" in content
    assert "### SmarTicket - Fix login bug" in content


def test_invalid_date(tmp_diario):
    """aggiungi_entry returns an error for invalid date format."""
    result = aggiungi_entry(
        progetto="Test",
        descrizione="Test",
        paragrafo_intro="Test",
        data="not-a-date",
    )

    assert "errore" in result


def test_with_riferimenti(tmp_diario):
    """aggiungi_entry includes references when provided."""
    with patch("mcp_cronos.tools.entries.get_today", return_value=date(2026, 4, 9)):
        result = aggiungi_entry(
            progetto="RefProject",
            descrizione="With refs",
            paragrafo_intro="Work with references.",
            repository="my-repo",
            branch="feature/test",
            jira_ticket="PROJ-123",
            jira_url="https://jira.example.com/PROJ-123",
            gitlab_mr="!42",
            gitlab_mr_url="https://gitlab.example.com/mr/42",
        )

    assert result["successo"] is True
    from pathlib import Path

    content = Path(result["file"]).read_text(encoding="utf-8")
    assert "**Riferimenti:**" in content
    assert "my-repo" in content
    assert "`feature/test`" in content
    assert "PROJ-123" in content
    assert "MR !42" in content


def test_imposta_bloccanti_updates(sample_diary_it):
    """imposta_bloccanti updates the blockers section in an existing file."""
    with patch("mcp_cronos.tools.entries.get_today", return_value=date(2026, 4, 9)):
        result = imposta_bloccanti(bloccanti="Waiting for API access")

    assert result["successo"] is True
    content = sample_diary_it.read_text(encoding="utf-8")
    assert "Waiting for API access" in content


def test_imposta_bloccanti_file_not_found(tmp_diario):
    """imposta_bloccanti returns an error when the diary file does not exist."""
    with patch("mcp_cronos.tools.entries.get_today", return_value=date(2026, 4, 9)):
        result = imposta_bloccanti(bloccanti="Some blocker")

    assert "errore" in result
    assert "non trovato" in result["errore"]
