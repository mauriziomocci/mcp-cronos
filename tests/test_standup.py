"""Tests for the standup tool module."""

from datetime import date
from unittest.mock import patch

from mcp_cronos.tools.standup import _determina_contesto_temporale, genera_riassunto_standup


def test_returns_style_instructions(sample_diary_it):
    """genera_riassunto_standup returns style instructions loaded from the template."""
    with patch("mcp_cronos.tools.standup.get_today", return_value=date(2026, 4, 10)):
        result = genera_riassunto_standup(data="2026-04-09")

    assert "istruzioni_stile" in result
    assert "ISTRUZIONI" in result["istruzioni_stile"]
    assert result["num_entries"] >= 1


def test_no_entries_returns_error(tmp_diario):
    """genera_riassunto_standup returns an error when no entries exist."""
    with patch("mcp_cronos.tools.standup.get_today", return_value=date(2026, 4, 10)):
        result = genera_riassunto_standup(data="2026-04-09")

    assert "errore" in result
    assert "Nessuna entry" in result["errore"]


def test_returns_projects_list(sample_diary_it):
    """genera_riassunto_standup returns the list of projects found."""
    with patch("mcp_cronos.tools.standup.get_today", return_value=date(2026, 4, 10)):
        result = genera_riassunto_standup(data="2026-04-09")

    assert "progetti" in result
    assert "MCP Cronos" in result["progetti"]


def test_temporal_context_yesterday(tmp_diario):
    """_determina_contesto_temporale returns 'Ieri' for yesterday's date."""
    today = date(2026, 4, 10)
    yesterday = date(2026, 4, 9)
    context = _determina_contesto_temporale([yesterday], today)
    assert "Ieri" in context


def test_temporal_context_range(tmp_diario):
    """_determina_contesto_temporale returns a range description for multiple dates."""
    today = date(2026, 4, 10)
    dates = [date(2026, 4, 7), date(2026, 4, 8), date(2026, 4, 9)]
    context = _determina_contesto_temporale(dates, today)
    # Should contain "Dal" ... "al" from the temporal pack
    assert "7" in context
    assert "9" in context


def test_date_range_query(sample_diary_it):
    """genera_riassunto_standup supports date range queries."""
    result = genera_riassunto_standup(
        data_inizio="2026-04-09",
        data_fine="2026-04-09",
    )

    assert "entries" in result
    assert result["num_entries"] >= 1


def test_invalid_date_range(tmp_diario):
    """genera_riassunto_standup returns error when start > end."""
    result = genera_riassunto_standup(
        data_inizio="2026-04-10",
        data_fine="2026-04-09",
    )

    assert "errore" in result


# ---------------------------------------------------------------------------
# Reuse of existing fine-giornata.md (closure already generated)
# ---------------------------------------------------------------------------


def _seed_new_layout_with_chiusura(tmp_diario, day, raw_content, chiusura_content):
    folder = tmp_diario / day[:4] / day[5:7] / day
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "raw.md").write_text(raw_content, encoding="utf-8")
    (folder / "fine-giornata.md").write_text(chiusura_content, encoding="utf-8")


def test_standup_reuses_chiusura_when_present(tmp_diario):
    """If fine-giornata.md exists with discorso/Q&A, return them in the response."""
    raw = (
        "# T\n\n## Cosa ho fatto ieri\n\n### Progetto - Desc\n\n"
        "Lavoro fatto.\n\n---\n\n## Bloccanti\n\nNessuno\n"
    )
    chiusura = (
        "# Chiusura\n\n## Riassunto\n\nbreve\n\n"
        "## Discorso per lo standup\n\n"
        "Ieri ho fatto questa cosa precisa.\n\n"
        "## Domande probabili e risposte pronte\n\n"
        "**D: che hai fatto?**\nR: il lavoro X.\n\n"
        "## Bloccanti\n\nNessuno\n"
    )
    _seed_new_layout_with_chiusura(tmp_diario, "2026-05-04", raw, chiusura)

    with patch("mcp_cronos.tools.standup.get_today", return_value=date(2026, 5, 5)):
        result = genera_riassunto_standup(data="2026-05-04")

    assert "chiusura_disponibile" in result
    assert "Ieri ho fatto questa cosa precisa" in result["chiusura_disponibile"]["discorso_standup"]
    assert "che hai fatto" in result["chiusura_disponibile"]["qa_standup"]
    assert "nota_riuso" in result


def test_standup_no_chiusura_no_reuse(tmp_diario):
    """If fine-giornata.md is missing, no `chiusura_disponibile` field."""
    raw = "# T\n\n## Cosa ho fatto ieri\n\n### P - D\n\nx\n\n---\n\n## Bloccanti\n\nNessuno\n"
    folder = tmp_diario / "2026" / "05" / "2026-05-04"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "raw.md").write_text(raw, encoding="utf-8")

    with patch("mcp_cronos.tools.standup.get_today", return_value=date(2026, 5, 5)):
        result = genera_riassunto_standup(data="2026-05-04")

    assert "chiusura_disponibile" not in result


def test_standup_legacy_does_not_reuse(tmp_diario):
    """For legacy single-file dates, no separate chiusura is searched."""
    legacy = tmp_diario / "2026" / "04" / "2026-04-09.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(
        "# T\n\n## Cosa ho fatto ieri\n\n### P - D\n\nx\n\n---\n\n## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )

    with patch("mcp_cronos.tools.standup.get_today", return_value=date(2026, 4, 10)):
        result = genera_riassunto_standup(data="2026-04-09")

    assert "chiusura_disponibile" not in result


def test_standup_multi_day_range_no_reuse(tmp_diario):
    """A multi-day range never triggers chiusura reuse (would mix days)."""
    chiusura = "# Closure\n\n## Discorso per lo standup\n\nx.\n\n## Domande probabili e risposte pronte\n\nQ\n"
    raw = "# T\n\n## Cosa ho fatto ieri\n\n### P - D\n\nx\n\n---\n\n## Bloccanti\n\nNessuno\n"
    for day in ("2026-05-04", "2026-05-05"):
        folder = tmp_diario / day[:4] / day[5:7] / day
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "raw.md").write_text(raw, encoding="utf-8")
        (folder / "fine-giornata.md").write_text(chiusura, encoding="utf-8")

    result = genera_riassunto_standup(
        data_inizio="2026-05-04",
        data_fine="2026-05-05",
    )

    assert "chiusura_disponibile" not in result
