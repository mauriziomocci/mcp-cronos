"""Tests for the prepara_domani tool module."""

from datetime import date
from pathlib import Path
from unittest.mock import patch

from mcp_cronos.tools.prepara_domani import prepara_domani


def _patch_today(d):
    """Patch get_today inside the prepara_domani module."""
    return patch("mcp_cronos.tools.prepara_domani.get_today", return_value=d)


def test_prepara_domani_writes_todo_and_raw_skeleton(tmp_diario):
    """A working day (Monday) calls in: todo.md created, raw.md skeleton created."""
    contenuto = "# Da fare martedi\n\n## 1. Verificare X\n"
    with _patch_today(date(2026, 5, 4)):  # lunedi
        result = prepara_domani(contenuto_todo=contenuto)

    assert result["successo"] is True
    assert result["data"] == "2026-05-05"
    assert result["raw_creato_adesso"] is True

    todo_path = tmp_diario / "2026" / "05" / "2026-05-05" / "todo.md"
    raw_path = tmp_diario / "2026" / "05" / "2026-05-05" / "raw.md"

    assert Path(result["todo_file"]) == todo_path
    assert Path(result["raw_file"]) == raw_path
    assert todo_path.read_text(encoding="utf-8") == contenuto
    # Skeleton standard: titolo standup + sezioni canoniche
    raw_content = raw_path.read_text(encoding="utf-8")
    assert "# Per lo Stand-up" in raw_content
    assert "## Cosa ho fatto ieri" in raw_content
    assert "## Bloccanti" in raw_content


def test_prepara_domani_friday_targets_monday(tmp_diario):
    """End-of-day on Friday must skip the weekend and prepare the next Monday."""
    with _patch_today(date(2026, 5, 8)):  # venerdi
        result = prepara_domani(contenuto_todo="# Da fare lunedi\n")

    assert result["data"] == "2026-05-11"  # lunedi successivo
    assert (tmp_diario / "2026" / "05" / "2026-05-11" / "todo.md").exists()
    assert (tmp_diario / "2026" / "05" / "2026-05-11" / "raw.md").exists()


def test_prepara_domani_explicit_date_overrides_default(tmp_diario):
    """When `data` is provided, the tool writes to that date regardless of weekday."""
    with _patch_today(date(2026, 5, 4)):  # lunedi
        result = prepara_domani(
            contenuto_todo="# Pianificato per giovedi\n",
            data="2026-05-14",
        )

    assert result["data"] == "2026-05-14"
    assert (tmp_diario / "2026" / "05" / "2026-05-14" / "todo.md").exists()


def test_prepara_domani_does_not_overwrite_existing_raw(tmp_diario):
    """If raw.md already exists for the target date, it must NOT be overwritten."""
    target_folder = tmp_diario / "2026" / "05" / "2026-05-05"
    target_folder.mkdir(parents=True, exist_ok=True)
    raw_path = target_folder / "raw.md"
    raw_path.write_text("# Entry gia scritta in anticipo\n", encoding="utf-8")

    with _patch_today(date(2026, 5, 4)):
        result = prepara_domani(contenuto_todo="# Todo nuovo\n")

    assert result["raw_creato_adesso"] is False
    # raw.md must keep the pre-existing content
    assert "# Entry gia scritta in anticipo" in raw_path.read_text(encoding="utf-8")


def test_prepara_domani_overwrites_existing_todo_and_keeps_backup(tmp_diario):
    """todo.md is the latest plan: re-running prepara_domani overwrites it but
    saves the previous content to todo.bak.md so manual annotations are not lost."""
    target_folder = tmp_diario / "2026" / "05" / "2026-05-05"
    target_folder.mkdir(parents=True, exist_ok=True)
    todo_path = target_folder / "todo.md"
    backup_path = target_folder / "todo.bak.md"
    todo_path.write_text("# Todo vecchio\n", encoding="utf-8")

    with _patch_today(date(2026, 5, 4)):
        result = prepara_domani(contenuto_todo="# Todo nuovo\n")

    assert result["successo"] is True
    assert result["todo_backup_creato"] is True
    assert todo_path.read_text(encoding="utf-8") == "# Todo nuovo\n"
    assert backup_path.read_text(encoding="utf-8") == "# Todo vecchio\n"


def test_prepara_domani_first_run_no_backup(tmp_diario):
    """When no previous todo exists, no backup file is created."""
    with _patch_today(date(2026, 5, 4)):
        result = prepara_domani(contenuto_todo="# Primo todo\n")

    assert result["todo_backup_creato"] is False
    assert result["backup_file"] is None
    backup_path = tmp_diario / "2026" / "05" / "2026-05-05" / "todo.bak.md"
    assert not backup_path.exists()


def test_prepara_domani_invalid_date(tmp_diario):
    """An invalid `data` returns an error."""
    result = prepara_domani(contenuto_todo="# x\n", data="not-a-date")
    assert "errore" in result
