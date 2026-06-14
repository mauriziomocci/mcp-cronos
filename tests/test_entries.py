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


# ---------------------------------------------------------------------------
# New folder layout: per-day folder with raw.md
# ---------------------------------------------------------------------------


def test_aggiungi_entry_uses_new_folder_layout_for_fresh_date(tmp_diario):
    """For a date with no legacy file, aggiungi_entry writes to <day>/raw.md."""
    from pathlib import Path

    with patch("mcp_cronos.tools.entries.get_today", return_value=date(2026, 5, 4)):
        result = aggiungi_entry(
            progetto="NuovoLayout",
            descrizione="Verifica cartella per giornata",
            paragrafo_intro="Test del nuovo layout.",
        )

    assert result["successo"] is True
    expected_raw = tmp_diario / "2026" / "05" / "2026-05-04" / "raw.md"
    assert Path(result["file"]) == expected_raw
    assert expected_raw.exists()
    assert "### NuovoLayout - Verifica cartella per giornata" in expected_raw.read_text(
        encoding="utf-8"
    )


def test_aggiungi_entry_appends_to_legacy_when_present(tmp_diario):
    """If the legacy single-file already exists, aggiungi_entry keeps using it."""
    from pathlib import Path

    legacy = tmp_diario / "2026" / "01" / "2026-01-21.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(
        "# Per lo Stand-up - 22 Gennaio 2026\n\n## Cosa ho fatto ieri\n\n## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )

    with patch("mcp_cronos.tools.entries.get_today", return_value=date(2026, 1, 21)):
        result = aggiungi_entry(
            progetto="Legacy",
            descrizione="Append a file storico",
            paragrafo_intro="Verifica retrocompatibilita'.",
        )

    assert result["successo"] is True
    assert Path(result["file"]) == legacy
    assert "### Legacy - Append a file storico" in legacy.read_text(encoding="utf-8")
    # No per-day folder must be created when legacy exists
    assert not (tmp_diario / "2026" / "01" / "2026-01-21").exists()


# ---------------------------------------------------------------------------
# Git auto-detection
# ---------------------------------------------------------------------------

import subprocess  # noqa: E402  (placed after existing imports for patch compat)


def _init_repo_e(path, branch="dev-branch"):
    subprocess.run(["git", "init", "-b", branch, str(path)], check=True, capture_output=True)
    (path / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-m", "i"],
        check=True, capture_output=True,
    )


def test_aggiungi_entry_autodetects_git(tmp_diario, tmp_path):
    from pathlib import Path

    from mcp_cronos.tools.entries import aggiungi_entry

    repo = tmp_path / "autorepo"
    repo.mkdir()
    _init_repo_e(repo, branch="dev-branch")

    result = aggiungi_entry(
        progetto="P", descrizione="D", paragrafo_intro="intro",
        data="2026-04-09", working_dir=str(repo),
    )
    content = Path(result["file"]).read_text(encoding="utf-8")
    assert "autorepo" in content
    assert "dev-branch" in content


def test_aggiungi_entry_explicit_repository_wins(tmp_diario, tmp_path):
    from pathlib import Path

    from mcp_cronos.tools.entries import aggiungi_entry

    repo = tmp_path / "autorepo"
    repo.mkdir()
    _init_repo_e(repo, branch="dev-branch")

    result = aggiungi_entry(
        progetto="P", descrizione="D", paragrafo_intro="intro", data="2026-04-09",
        repository="explicit-repo", working_dir=str(repo),
    )
    content = Path(result["file"]).read_text(encoding="utf-8")
    assert "explicit-repo" in content
    assert "autorepo" not in content
