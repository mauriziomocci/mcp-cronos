"""Tests for the leggi_todo tool module."""

from datetime import date
from pathlib import Path
from unittest.mock import patch

from mcp_cronos.tools.leggi_todo import leggi_todo


def _patch_today(d):
    return patch("mcp_cronos.tools.leggi_todo.get_today", return_value=d)


def test_leggi_todo_returns_content_when_file_exists(tmp_diario):
    folder = tmp_diario / "2026" / "05" / "2026-05-04"
    folder.mkdir(parents=True, exist_ok=True)
    todo_path = folder / "todo.md"
    todo_path.write_text("# Da fare\n\n## 1. cosa importante\n", encoding="utf-8")

    with _patch_today(date(2026, 5, 4)):
        result = leggi_todo()

    assert "errore" not in result
    assert result["data"] == "2026-05-04"
    assert Path(result["file"]) == todo_path
    assert "## 1. cosa importante" in result["contenuto"]
    assert result["backup"] is None


def test_leggi_todo_explicit_date(tmp_diario):
    folder = tmp_diario / "2026" / "05" / "2026-05-11"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "todo.md").write_text("contenuto x", encoding="utf-8")

    result = leggi_todo(data="2026-05-11")
    assert result["successo"] is True
    assert result["contenuto"] == "contenuto x"


def test_leggi_todo_returns_backup_info_when_present(tmp_diario):
    folder = tmp_diario / "2026" / "05" / "2026-05-04"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "todo.md").write_text("nuovo", encoding="utf-8")
    (folder / "todo.bak.md").write_text("precedente piu lungo", encoding="utf-8")

    with _patch_today(date(2026, 5, 4)):
        result = leggi_todo()

    assert result["backup"] is not None
    assert result["backup"]["file"].endswith("todo.bak.md")
    assert result["backup"]["dimensione"] > 0


def test_leggi_todo_missing_file(tmp_diario):
    with _patch_today(date(2026, 5, 4)):
        result = leggi_todo()

    assert "errore" in result
    assert "non trovato" in result["errore"]


def test_leggi_todo_invalid_date(tmp_diario):
    result = leggi_todo(data="bad")
    assert "errore" in result
