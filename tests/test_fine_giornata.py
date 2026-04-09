"""Tests for the fine_giornata tool module."""

import importlib
from datetime import date
from unittest.mock import patch

# The __init__.py re-exports a function named `fine_giornata`, shadowing the module.
# Use importlib to get the actual module object for patch.object.
_fg_mod = importlib.import_module("mcp_cronos.tools.fine_giornata")
from mcp_cronos.tools.fine_giornata import fine_giornata  # noqa: E402


def _patch_today(d):
    """Return a patch context manager for get_today in the fine_giornata module."""
    return patch.object(_fg_mod, "get_today", return_value=d)


def test_returns_instructions(sample_diary_it):
    """fine_giornata returns style instructions and parsed entries."""
    with _patch_today(date(2026, 4, 9)):
        result = fine_giornata()

    assert "istruzioni" in result
    assert "ISTRUZIONI" in result["istruzioni"]
    assert result["data"] == "2026-04-09"
    assert str(sample_diary_it) == result["file"]


def test_file_not_found(tmp_diario):
    """fine_giornata returns an error when no diary file exists for the date."""
    with _patch_today(date(2026, 4, 9)):
        result = fine_giornata()

    assert "errore" in result
    assert "non trovato" in result["errore"]


def test_returns_entries_or_content(sample_diary_it):
    """fine_giornata returns either parsed entries or full content."""
    with _patch_today(date(2026, 4, 9)):
        result = fine_giornata()

    # Should have either structured entries or free-form content
    has_entries = "entries" in result
    has_content = "contenuto_completo" in result
    assert has_entries or has_content

    if has_entries:
        assert result["num_entries"] >= 1
        assert len(result["progetti"]) >= 1


def test_returns_blockers(sample_diary_it):
    """fine_giornata includes the blockers section from the diary."""
    with _patch_today(date(2026, 4, 9)):
        result = fine_giornata()

    assert "bloccanti" in result


def test_template_uses_config_sections(sample_diary_it):
    """The style instructions contain the configured section names."""
    with _patch_today(date(2026, 4, 9)):
        result = fine_giornata()

    instructions = result["istruzioni"]
    # Default Italian config sections should appear in the template
    assert "Bloccanti" in instructions
