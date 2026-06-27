"""Tests for the scrivi_fine_giornata tool module."""

import sys
from datetime import date
from pathlib import Path  # noqa: F401 — used in assertions
from unittest.mock import MagicMock, patch

# Access the actual module object to avoid the __init__.py function shadowing
_scrivi_mod = sys.modules.get("mcp_cronos.tools.scrivi_fine_giornata")
if _scrivi_mod is None:
    import importlib

    _scrivi_mod = importlib.import_module("mcp_cronos.tools.scrivi_fine_giornata")

from mcp_cronos.tools.scrivi_fine_giornata import (  # noqa: E402
    _git_commit_and_push,
    scrivi_fine_giornata,
)


def _patch_today(d):
    """Return a patch context manager for get_today in the scrivi module."""
    return patch.object(_scrivi_mod, "get_today", return_value=d)


def test_writes_file(tmp_diario, config_toml_it):
    """scrivi_fine_giornata writes the markdown content to the correct file."""
    content = "# Test diary\n\nSome content.\n"
    with _patch_today(date(2026, 4, 9)):
        result = scrivi_fine_giornata(contenuto=content)

    assert result["successo"] is True
    assert result["dimensione"] == len(content)
    written = Path(result["file"]).read_text(encoding="utf-8")
    assert written == content


def test_git_disabled(tmp_diario, config_toml_it):
    """When git is disabled via config, _git_commit_and_push returns disabled status."""
    result = _git_commit_and_push(date(2026, 4, 9))
    assert result == {"git": "disabled"}


def test_git_disabled_in_scrivi(tmp_diario, config_toml_it):
    """scrivi_fine_giornata reports git disabled when config says so."""
    content = "# Test\n"
    with _patch_today(date(2026, 4, 9)):
        result = scrivi_fine_giornata(contenuto=content)

    assert result["git"] == {"git": "disabled"}


def test_git_commit_and_push(tmp_diario):
    """_git_commit_and_push stages the whole diary and calls git commands when enabled."""
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text(
        '[cronos]\nlang = "it"\n\n[cronos.git]\nenabled = true\nauto_push = true\n',
        encoding="utf-8",
    )

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch.object(_scrivi_mod.subprocess, "run", return_value=mock_result) as mock_run:
        result = _git_commit_and_push(date(2026, 4, 9))

    assert result["git_add"] == "ok"
    assert result["git_commit"] == "ok"
    assert result["git_push"] == "ok"
    assert mock_run.call_count == 3
    # Verify the add uses -A (whole diary), not a single file path.
    add_call_args = mock_run.call_args_list[0][0][0]
    assert add_call_args == ["git", "add", "-A"]


def test_git_auto_push_disabled(tmp_diario):
    """_git_commit_and_push skips push when auto_push is false."""
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text(
        '[cronos]\nlang = "it"\n\n[cronos.git]\nenabled = true\nauto_push = false\n',
        encoding="utf-8",
    )

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch.object(_scrivi_mod.subprocess, "run", return_value=mock_result) as mock_run:
        result = _git_commit_and_push(date(2026, 4, 9))

    assert result["git_add"] == "ok"
    assert result["git_commit"] == "ok"
    assert result["git_push"] == "skipped (auto_push disabled)"
    assert mock_run.call_count == 2


def test_invalid_date(tmp_diario):
    """scrivi_fine_giornata returns an error for an invalid date."""
    result = scrivi_fine_giornata(contenuto="# Test\n", data="bad-date")
    assert "errore" in result


# ---------------------------------------------------------------------------
# New folder layout: closure file separated from raw entries
# ---------------------------------------------------------------------------


def test_scrivi_uses_new_layout_for_fresh_date(tmp_diario, config_toml_it):
    """For a date with no legacy file, scrivi_fine_giornata writes to <day>/fine-giornata.md."""
    content = "# Closure\n\nSlim summary.\n"
    with _patch_today(date(2026, 5, 4)):
        result = scrivi_fine_giornata(contenuto=content)

    expected_path = tmp_diario / "2026" / "05" / "2026-05-04" / "fine-giornata.md"
    assert result["successo"] is True
    assert Path(result["file"]) == expected_path
    assert expected_path.read_text(encoding="utf-8") == content


def test_scrivi_uses_legacy_when_present(tmp_diario, config_toml_it):
    """When the legacy single-file exists, scrivi_fine_giornata writes to it (no folder split)."""
    legacy = tmp_diario / "2026" / "04" / "2026-04-09.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("preexisting raw content", encoding="utf-8")

    content = "# Closure on legacy\n\nReplaces in-place.\n"
    with _patch_today(date(2026, 4, 9)):
        result = scrivi_fine_giornata(contenuto=content)

    assert result["successo"] is True
    assert Path(result["file"]) == legacy
    assert legacy.read_text(encoding="utf-8") == content
    # No per-day folder should be created when the legacy file already exists
    assert not (tmp_diario / "2026" / "04" / "2026-04-09").exists()


def test_scrivi_does_not_overwrite_raw_in_new_layout(tmp_diario, config_toml_it):
    """raw.md and fine-giornata.md must coexist in the per-day folder without overlap."""
    raw_path = tmp_diario / "2026" / "05" / "2026-05-04" / "raw.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("# Raw entries of the day\n\nDetailed log.\n", encoding="utf-8")

    closure = "# Closure\n\nKey points only.\n"
    with _patch_today(date(2026, 5, 4)):
        result = scrivi_fine_giornata(contenuto=closure)

    fine_path = tmp_diario / "2026" / "05" / "2026-05-04" / "fine-giornata.md"
    assert Path(result["file"]) == fine_path
    assert fine_path.read_text(encoding="utf-8") == closure
    # raw.md must remain untouched
    assert "Detailed log." in raw_path.read_text(encoding="utf-8")


def test_scrivi_fine_giornata_with_contenuto_todo_prepares_next_day(tmp_diario, config_toml_it):
    from pathlib import Path

    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.scrivi_fine_giornata import scrivi_fine_giornata

    _reset_config()
    result = scrivi_fine_giornata(
        contenuto="# Chiusura\n\nfatto.\n",
        data="2026-04-09",
        contenuto_todo="- [ ] domani task\n",
    )
    assert result["successo"] is True
    assert "prepara_domani" in result
    assert result["prepara_domani"]["successo"] is True
    assert Path(result["prepara_domani"]["todo_file"]).exists()


def test_scrivi_fine_giornata_without_todo_unchanged(tmp_diario, config_toml_it):
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.scrivi_fine_giornata import scrivi_fine_giornata

    _reset_config()
    result = scrivi_fine_giornata(contenuto="# Chiusura\n\nfatto.\n", data="2026-04-09")
    assert result["successo"] is True
    assert "prepara_domani" not in result


# ---------------------------------------------------------------------------
# Git integration tests: whole-diary staging and commit ordering
# ---------------------------------------------------------------------------

import subprocess  # noqa: E402


def _init_diary_git_repo(diario):
    """Init a git repo at the diary root with git enabled, push disabled."""
    (diario / "cronos.toml").write_text(
        "[cronos.git]\nenabled = true\nauto_push = false\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-b", "main", str(diario)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(diario), "-c", "user.email=t@t", "-c", "user.name=t",
         "add", "-A"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(diario), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-m", "init"],
        check=True, capture_output=True,
    )


def _porcelain(diario):
    out = subprocess.run(
        ["git", "-C", str(diario), "status", "--porcelain"],
        check=True, capture_output=True, text=True,
    )
    return out.stdout.strip()


def test_end_of_day_commits_whole_day(tmp_diario, monkeypatch):
    # git needs an identity for the commit made by the tool
    monkeypatch.setenv("GIT_AUTHOR_NAME", "t")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "t@t")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "t")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "t@t")
    _init_diary_git_repo(tmp_diario)

    # Simulate a day's progressive log written during the day (uncommitted).
    day_dir = tmp_diario / "2026" / "04" / "2026-04-09"
    day_dir.mkdir(parents=True, exist_ok=True)
    (day_dir / "raw.md").write_text("# raw\n\n## Cosa ho fatto ieri\n\nwork\n", encoding="utf-8")

    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.scrivi_fine_giornata import scrivi_fine_giornata

    _reset_config()
    result = scrivi_fine_giornata(contenuto="# Chiusura\n\ndone\n", data="2026-04-09")

    assert result["successo"] is True
    assert result["git"]["git_commit"] == "ok"
    # The whole diary must be clean: raw.md AND fine-giornata.md both committed.
    assert _porcelain(tmp_diario) == ""


def test_end_of_day_with_todo_commits_next_day_too(tmp_diario, monkeypatch):
    monkeypatch.setenv("GIT_AUTHOR_NAME", "t")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "t@t")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "t")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "t@t")
    _init_diary_git_repo(tmp_diario)

    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.scrivi_fine_giornata import scrivi_fine_giornata

    _reset_config()
    result = scrivi_fine_giornata(
        contenuto="# Chiusura\n", data="2026-04-09", contenuto_todo="- [ ] task\n"
    )

    assert result["prepara_domani"]["successo"] is True
    # Next-day files prepared by prepara_domani must also be committed.
    assert _porcelain(tmp_diario) == ""
