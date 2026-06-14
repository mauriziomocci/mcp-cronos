"""Tests for the cerca tool module (cerca_nel_diario)."""

from datetime import date
from unittest.mock import patch

from mcp_cronos.tools.cerca import cerca_nel_diario


def test_finds_match(sample_diary_it):
    """cerca_nel_diario finds entries matching the query."""
    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 4, 9)):
        result = cerca_nel_diario(
            query="config",
            data_inizio="2026-04-09",
            data_fine="2026-04-09",
        )

    assert result["totale_risultati"] >= 1
    assert result["risultati"][0]["progetto"] == "MCP Cronos"


def test_no_match(sample_diary_it):
    """cerca_nel_diario returns zero results when nothing matches."""
    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 4, 9)):
        result = cerca_nel_diario(
            query="xyznonexistent",
            data_inizio="2026-04-09",
            data_fine="2026-04-09",
        )

    assert result["totale_risultati"] == 0


def test_invalid_regex(tmp_diario):
    """cerca_nel_diario returns an error for an invalid regex pattern."""
    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 4, 9)):
        result = cerca_nel_diario(query="[invalid")

    assert "errore" in result
    assert "regex" in result["errore"].lower()


def test_case_insensitive(sample_diary_it):
    """cerca_nel_diario performs case-insensitive searches."""
    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 4, 9)):
        result = cerca_nel_diario(
            query="CONFIG",
            data_inizio="2026-04-09",
            data_fine="2026-04-09",
        )

    assert result["totale_risultati"] >= 1


def test_no_files_in_range(tmp_diario):
    """cerca_nel_diario returns zero results when no files exist in the range."""
    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 4, 9)):
        result = cerca_nel_diario(
            query="anything",
            data_inizio="2026-04-01",
            data_fine="2026-04-09",
        )

    assert result["totale_risultati"] == 0
    assert result["files_cercati"] == 0


# ---------------------------------------------------------------------------
# Multi-source search (raw / todo / chiusura)
# ---------------------------------------------------------------------------


def _make_new_layout_day(tmp_diario, day, raw=None, todo=None, chiusura=None):
    folder = tmp_diario / day[:4] / day[5:7] / day
    folder.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        (folder / "raw.md").write_text(raw, encoding="utf-8")
    if todo is not None:
        (folder / "todo.md").write_text(todo, encoding="utf-8")
    if chiusura is not None:
        (folder / "fine-giornata.md").write_text(chiusura, encoding="utf-8")


def test_cerca_default_searches_all_sources(tmp_diario):
    """Default behavior: search across raw, todo, chiusura."""
    _make_new_layout_day(
        tmp_diario,
        "2026-05-04",
        raw=(
            "# T\n\n## Cosa ho fatto ieri\n\n### Progetto - Desc\n\n"
            "Lavoro su cleartokens.\n\n---\n\n## Bloccanti\n\nNessuno\n"
        ),
        todo="# Da fare\n\n## 1. Verificare cleartokens\n",
        chiusura="# Closure\n\n## Decisioni\n\nDeciso di sospendere il cron cleartokens\n",
    )

    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 5, 4)):
        result = cerca_nel_diario(
            query="cleartokens",
            data_inizio="2026-05-04",
            data_fine="2026-05-04",
        )

    tipi = {r["tipo"] for r in result["risultati"]}
    assert tipi == {"raw", "todo", "chiusura"}
    assert result["totale_risultati"] == 3


def test_cerca_filtra_solo_chiusura(tmp_diario):
    """tipo=['chiusura'] limits the search to fine-giornata.md."""
    _make_new_layout_day(
        tmp_diario,
        "2026-05-04",
        raw="# T\n\n## Cosa ho fatto ieri\n\n### P - D\n\ncleartokens raw\n\n## Bloccanti\n\nNessuno\n",
        todo="# Da fare\n\ncleartokens nel todo\n",
        chiusura="# C\n\n## Decisioni\n\ncleartokens chiusura\n",
    )

    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 5, 4)):
        result = cerca_nel_diario(
            query="cleartokens",
            data_inizio="2026-05-04",
            data_fine="2026-05-04",
            tipo=["chiusura"],
        )

    assert result["tipo"] == ["chiusura"]
    assert result["totale_risultati"] == 1
    assert result["risultati"][0]["tipo"] == "chiusura"


def test_cerca_legacy_skips_todo_and_chiusura(tmp_diario):
    """For dates with legacy single-file, todo/chiusura sorgenti are skipped silently."""
    legacy = tmp_diario / "2026" / "04" / "2026-04-09.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(
        "# T\n\n## Cosa ho fatto ieri\n\n### P - D\n\nlegacy match\n\n---\n\n## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )

    with patch("mcp_cronos.tools.cerca.get_today", return_value=date(2026, 4, 9)):
        result = cerca_nel_diario(
            query="legacy",
            data_inizio="2026-04-09",
            data_fine="2026-04-09",
        )

    assert all(r["tipo"] == "raw" for r in result["risultati"])
    assert result["totale_risultati"] == 1


def test_cerca_invalid_tipo_returns_error(tmp_diario):
    result = cerca_nel_diario(query="x", tipo=["bogus"])
    assert "errore" in result
    assert "bogus" in result["errore"]


def test_cerca_caps_results_and_reports_truncation(tmp_diario):
    from mcp_cronos.tools.cerca import cerca_nel_diario

    month_dir = tmp_diario / "2026" / "04"
    month_dir.mkdir(parents=True, exist_ok=True)
    (month_dir / "2026-04-09.md").write_text(
        "# Per lo Stand-up - 10 Aprile 2026\n\n"
        "## Cosa ho fatto ieri\n\n"
        "### Alpha - widget\n\nwidget work\n\n---\n\n"
        "### Beta - widget\n\nwidget work\n\n---\n\n"
        "### Gamma - widget\n\nwidget work\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )

    result = cerca_nel_diario(
        query="widget",
        data_inizio="2026-04-09",
        data_fine="2026-04-09",
        tipo=["raw"],
        max_risultati=2,
    )

    assert result["totale_risultati"] == 3
    assert len(result["risultati"]) == 2
    assert result["troncato"] is True
    assert result["max_risultati"] == 2
    assert "nota" in result


def test_cerca_no_truncation_under_limit(tmp_diario):
    from mcp_cronos.tools.cerca import cerca_nel_diario

    month_dir = tmp_diario / "2026" / "04"
    month_dir.mkdir(parents=True, exist_ok=True)
    (month_dir / "2026-04-09.md").write_text(
        "# Per lo Stand-up - 10 Aprile 2026\n\n"
        "## Cosa ho fatto ieri\n\n"
        "### Alpha - widget\n\nwidget work\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )

    result = cerca_nel_diario(
        query="widget",
        data_inizio="2026-04-09",
        data_fine="2026-04-09",
        tipo=["raw"],
    )

    assert result["totale_risultati"] == 1
    assert result["troncato"] is False
    assert result["max_risultati"] == 50
    assert "nota" not in result


def test_cerca_at_exact_limit_not_truncated(tmp_diario):
    from mcp_cronos.tools.cerca import cerca_nel_diario

    month_dir = tmp_diario / "2026" / "04"
    month_dir.mkdir(parents=True, exist_ok=True)
    (month_dir / "2026-04-09.md").write_text(
        "# Per lo Stand-up - 10 Aprile 2026\n\n"
        "## Cosa ho fatto ieri\n\n"
        "### Alpha - widget\n\nwidget work\n\n---\n\n"
        "### Beta - widget\n\nwidget work\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )

    result = cerca_nel_diario(
        query="widget",
        data_inizio="2026-04-09",
        data_fine="2026-04-09",
        tipo=["raw"],
        max_risultati=2,
    )

    assert result["totale_risultati"] == 2
    assert len(result["risultati"]) == 2
    assert result["troncato"] is False
    assert "nota" not in result
