"""
End-to-end integration test for the full diary cycle.

Simulates a realistic two-day workflow over the new folder layout:

  Day 1 (Mon 2026-05-04):
    - aggiungi_entry su un progetto
    - imposta_bloccanti
    - fine_giornata (read raw)
    - scrivi_fine_giornata (closure with discorso/Q&A)
    - prepara_domani (seed Day 2 with todo + raw skeleton)

  Day 2 (Tue 2026-05-05):
    - leggi_todo (verifies todo seeded the night before)
    - aggiungi_entry on the seeded raw skeleton (no overwrite)
    - cerca_nel_diario across raw / todo / chiusura

The goal is to catch regressions across tool boundaries that unit tests on
single tools would miss.
"""

import importlib
from datetime import date
from pathlib import Path
from unittest.mock import patch

# The tools package re-exports several function names from the modules,
# which shadows the module attribute. Resolve module references via
# importlib so patch.object targets the right namespace.
_entries_mod = importlib.import_module("mcp_cronos.tools.entries")
_fg_mod = importlib.import_module("mcp_cronos.tools.fine_giornata")
_scrivi_mod = importlib.import_module("mcp_cronos.tools.scrivi_fine_giornata")
_prepara_mod = importlib.import_module("mcp_cronos.tools.prepara_domani")
_leggi_todo_mod = importlib.import_module("mcp_cronos.tools.leggi_todo")
_cerca_mod = importlib.import_module("mcp_cronos.tools.cerca")

from mcp_cronos.tools.cerca import cerca_nel_diario  # noqa: E402
from mcp_cronos.tools.entries import aggiungi_entry, imposta_bloccanti  # noqa: E402
from mcp_cronos.tools.fine_giornata import fine_giornata  # noqa: E402
from mcp_cronos.tools.leggi_todo import leggi_todo  # noqa: E402
from mcp_cronos.tools.prepara_domani import prepara_domani  # noqa: E402
from mcp_cronos.tools.scrivi_fine_giornata import scrivi_fine_giornata  # noqa: E402


def _patches_for(day):
    """Build the list of get_today patches for every tool module used in the e2e flow."""
    return [
        patch.object(_entries_mod, "get_today", return_value=day),
        patch.object(_fg_mod, "get_today", return_value=day),
        patch.object(_scrivi_mod, "get_today", return_value=day),
        patch.object(_prepara_mod, "get_today", return_value=day),
        patch.object(_leggi_todo_mod, "get_today", return_value=day),
        patch.object(_cerca_mod, "get_today", return_value=day),
    ]


def _start(patches):
    for p in patches:
        p.start()


def _stop(patches):
    for p in patches:
        p.stop()


def test_full_two_day_cycle(tmp_diario, config_toml_it):
    """Run the realistic cycle over two consecutive working days."""
    day1 = date(2026, 5, 4)  # lunedi
    day2 = date(2026, 5, 5)  # martedi

    folder1 = tmp_diario / "2026" / "05" / "2026-05-04"
    folder2 = tmp_diario / "2026" / "05" / "2026-05-05"

    # ----- DAY 1 -----
    p1 = _patches_for(day1)
    _start(p1)
    try:
        # 1) Add a couple of entries
        r = aggiungi_entry(
            progetto="ATPSS",
            descrizione="Suspend appmanager vacuum cron",
            paragrafo_intro="Sospeso vacuum cron prima della saturazione PVC.",
        )
        assert r["successo"] is True
        assert (folder1 / "raw.md").exists()

        r = aggiungi_entry(
            progetto="MCP Cronos",
            descrizione="Refactor layout cartella per giorno",
            paragrafo_intro="Aggiunto todo.md e prepara_domani.",
        )
        assert r["successo"] is True

        # 2) Set blockers
        r = imposta_bloccanti(bloccanti="Attesa autorizzazione resize PVC")
        assert r["successo"] is True

        # 3) Read raw via fine_giornata
        r = fine_giornata()
        assert "errore" not in r
        assert r["num_entries"] == 2

        # 4) Write closure (slim)
        chiusura = (
            "# Per lo Stand-up - 5 Maggio 2026\n\n"
            "## Riassunto\n\nGiornata su ATPSS e refactor cronos.\n\n"
            "## Discorso per lo standup\n\n"
            "Ieri ho lavorato su ATPSS e su cronos.\n\n"
            "## Domande probabili e risposte pronte\n\n"
            "**D: rischi su ATPSS?**\nR: Nessuno immediato.\n\n"
            "## Bloccanti\n\nAttesa autorizzazione resize PVC\n"
        )
        r = scrivi_fine_giornata(contenuto=chiusura)
        assert r["successo"] is True
        assert Path(r["file"]) == folder1 / "fine-giornata.md"
        # Raw must be untouched
        assert "ATPSS - Suspend appmanager" in (folder1 / "raw.md").read_text(encoding="utf-8")

        # 5) Seed Day 2
        todo_domani = (
            "# Da fare martedi 5 maggio 2026\n\n"
            "## 1. Verificare esito vacuum notte\n\n"
            "Controllare jobs prod-teseoapp-atpss.\n"
        )
        r = prepara_domani(contenuto_todo=todo_domani)
        assert r["successo"] is True
        assert r["data"] == "2026-05-05"
        assert r["raw_creato_adesso"] is True
        assert r["todo_backup_creato"] is False
        assert (folder2 / "todo.md").exists()
        assert (folder2 / "raw.md").exists()
    finally:
        _stop(p1)

    # ----- DAY 2 -----
    p2 = _patches_for(day2)
    _start(p2)
    try:
        # 6) Read todo for today
        r = leggi_todo()
        assert "errore" not in r
        assert "Verificare esito vacuum notte" in r["contenuto"]

        # 7) Add entry on the seeded raw skeleton (must not lose the skeleton)
        r = aggiungi_entry(
            progetto="ATPSS",
            descrizione="Verifica vacuum notturno",
            paragrafo_intro="4 vacuum OK, appmanager sospeso come previsto.",
        )
        assert r["successo"] is True
        raw_day2 = (folder2 / "raw.md").read_text(encoding="utf-8")
        assert "### ATPSS - Verifica vacuum notturno" in raw_day2

        # 8) Cross-source search must find matches in raw and todo
        r = cerca_nel_diario(
            query="vacuum",
            data_inizio="2026-05-04",
            data_fine="2026-05-05",
        )
        tipi = {item["tipo"] for item in r["risultati"]}
        assert "raw" in tipi
        assert "todo" in tipi

        # Specific source filter
        r_solo_todo = cerca_nel_diario(
            query="vacuum",
            data_inizio="2026-05-04",
            data_fine="2026-05-05",
            tipo=["todo"],
        )
        assert all(item["tipo"] == "todo" for item in r_solo_todo["risultati"])
        assert r_solo_todo["totale_risultati"] >= 1
    finally:
        _stop(p2)
