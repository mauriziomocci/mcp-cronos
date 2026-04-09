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
    file_path = tmp_diario / "2026" / "04" / "2026-04-09.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("test", encoding="utf-8")

    result = _git_commit_and_push(file_path, date(2026, 4, 9))
    assert result == {"git": "disabled"}


def test_git_disabled_in_scrivi(tmp_diario, config_toml_it):
    """scrivi_fine_giornata reports git disabled when config says so."""
    content = "# Test\n"
    with _patch_today(date(2026, 4, 9)):
        result = scrivi_fine_giornata(contenuto=content)

    assert result["git"] == {"git": "disabled"}


def test_git_commit_and_push(tmp_diario):
    """_git_commit_and_push calls git commands when git is enabled."""
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text(
        '[cronos]\nlang = "it"\n\n[cronos.git]\nenabled = true\nauto_push = true\n',
        encoding="utf-8",
    )

    file_path = tmp_diario / "2026" / "04" / "2026-04-09.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("test content", encoding="utf-8")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch.object(_scrivi_mod.subprocess, "run", return_value=mock_result) as mock_run:
        result = _git_commit_and_push(file_path, date(2026, 4, 9))

    assert result["git_add"] == "ok"
    assert result["git_commit"] == "ok"
    assert result["git_push"] == "ok"
    assert mock_run.call_count == 3


def test_git_auto_push_disabled(tmp_diario):
    """_git_commit_and_push skips push when auto_push is false."""
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text(
        '[cronos]\nlang = "it"\n\n[cronos.git]\nenabled = true\nauto_push = false\n',
        encoding="utf-8",
    )

    file_path = tmp_diario / "2026" / "04" / "2026-04-09.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("test content", encoding="utf-8")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch.object(_scrivi_mod.subprocess, "run", return_value=mock_result) as mock_run:
        result = _git_commit_and_push(file_path, date(2026, 4, 9))

    assert result["git_add"] == "ok"
    assert result["git_commit"] == "ok"
    assert result["git_push"] == "skipped (auto_push disabled)"
    assert mock_run.call_count == 2


def test_invalid_date(tmp_diario):
    """scrivi_fine_giornata returns an error for an invalid date."""
    result = scrivi_fine_giornata(contenuto="# Test\n", data="bad-date")
    assert "errore" in result
