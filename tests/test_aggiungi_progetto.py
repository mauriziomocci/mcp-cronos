"""Tests for the aggiungi_progetto tool module."""

from datetime import date
from pathlib import Path
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


def test_with_references(tmp_diario, config_toml_it):
    """aggiungi_a_progetto includes references in the generated markdown (Italian config)."""
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


def test_crea_nuova_entry_uses_english_labels(tmp_diario, config_toml_en):
    """A brand-new entry created under English config uses English labels."""
    result = aggiungi_a_progetto(
        progetto="MCP Cronos",
        titolo_fase="Localise labels",
        contenuto="Body.",
        richiesto_da="Marco",
        repository="mcp-cronos",
        data="2026-04-09",
    )
    content = Path(result["file"]).read_text(encoding="utf-8")
    assert "*-Requested by Marco-*" in content
    assert "**References:**" in content
    assert "Riferimenti" not in content
    assert "Richiesto da" not in content


def test_aggiungi_fase_uses_english_labels(tmp_diario, config_toml_en):
    """Appending a phase to an existing entry under English config uses English labels."""
    aggiungi_a_progetto(
        progetto="MCP Cronos",
        titolo_fase="First phase",
        contenuto="First body.",
        data="2026-04-09",
    )
    result = aggiungi_a_progetto(
        progetto="MCP Cronos",
        titolo_fase="Second phase",
        contenuto="Second body.",
        richiesto_da="Marco",
        repository="mcp-cronos",
        data="2026-04-09",
    )
    content = Path(result["file"]).read_text(encoding="utf-8")
    assert result["modalita"] == "aggiunto_a_esistente"
    assert "*-Requested by Marco-*" in content
    assert "**References:**" in content


# ---------------------------------------------------------------------------
# Git auto-detection
# ---------------------------------------------------------------------------


def test_aggiungi_a_progetto_autodetects_git(tmp_diario, tmp_path):
    import subprocess

    from mcp_cronos.tools.aggiungi_progetto import aggiungi_a_progetto

    repo = tmp_path / "projrepo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "qa", str(repo)], check=True, capture_output=True)
    (repo / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-m", "i"],
        check=True, capture_output=True,
    )

    result = aggiungi_a_progetto(
        progetto="P", titolo_fase="F", contenuto="C",
        data="2026-04-09", working_dir=str(repo),
    )
    content = Path(result["file"]).read_text(encoding="utf-8")
    assert "projrepo" in content
    assert "qa" in content
