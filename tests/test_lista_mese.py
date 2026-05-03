"""Tests for the lista_mese tool module."""

from datetime import date
from unittest.mock import patch

from mcp_cronos.tools.lista_mese import lista_mese


def _patch_today(d):
    return patch("mcp_cronos.tools.lista_mese.get_today", return_value=d)


def test_lista_mese_default_uses_today(tmp_diario):
    """Default uses current month/year derived from today."""
    with _patch_today(date(2026, 5, 15)):
        result = lista_mese()

    assert result["anno"] == 2026
    assert result["mese"] == 5
    assert result["giorni_nel_mese"] == 31
    assert len(result["giorni"]) == 31


def test_lista_mese_explicit_month(tmp_diario):
    """Explicit mese/anno overrides today."""
    with _patch_today(date(2026, 5, 15)):
        result = lista_mese(mese=4, anno=2026)

    assert result["anno"] == 2026
    assert result["mese"] == 4
    assert result["giorni_nel_mese"] == 30


def test_lista_mese_detects_legacy(tmp_diario):
    """A legacy single-file day is reported with legacy=True."""
    legacy = tmp_diario / "2026" / "04" / "2026-04-09.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(
        "# T\n\n## Cosa ho fatto ieri\n\n### P - D\n\nx\n\n---\n\n## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )

    result = lista_mese(mese=4, anno=2026)
    giorno_9 = next(g for g in result["giorni"] if g["data"] == "2026-04-09")
    assert giorno_9["legacy"] is True
    assert giorno_9["raw"] is False
    assert giorno_9["num_entries"] == 1
    assert result["riepilogo"]["giorni_legacy"] == 1


def test_lista_mese_detects_new_layout_files(tmp_diario):
    """A new-layout day reports raw/todo/chiusura flags independently."""
    folder = tmp_diario / "2026" / "05" / "2026-05-04"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "raw.md").write_text(
        "# T\n\n## Cosa ho fatto ieri\n\n### P - D\n\nx\n\n---\n\n## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )
    (folder / "todo.md").write_text("# Da fare\n", encoding="utf-8")
    (folder / "fine-giornata.md").write_text("# Chiusura\n", encoding="utf-8")

    result = lista_mese(mese=5, anno=2026)
    giorno_4 = next(g for g in result["giorni"] if g["data"] == "2026-05-04")
    assert giorno_4["legacy"] is False
    assert giorno_4["raw"] is True
    assert giorno_4["todo"] is True
    assert giorno_4["chiusura"] is True
    assert giorno_4["num_entries"] == 1
    assert result["riepilogo"]["giorni_raw"] == 1
    assert result["riepilogo"]["giorni_con_todo"] == 1
    assert result["riepilogo"]["giorni_con_chiusura"] == 1


def test_lista_mese_invalid_month(tmp_diario):
    result = lista_mese(mese=13, anno=2026)
    assert "errore" in result
