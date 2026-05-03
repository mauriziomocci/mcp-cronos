"""
Tests for template_loader.py — built-in template loading and user override logic.

Covers:
- All three built-in templates load without error
- User override from diary directory takes precedence
- Unknown template name raises FileNotFoundError
- fine_giornata template contains all required section placeholders
"""

import os
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Built-in template loading
# ---------------------------------------------------------------------------


def test_load_builtin_fine_giornata():
    """Load the built-in fine_giornata template without error."""
    from mcp_cronos.template_loader import load_template

    content = load_template("fine_giornata")
    assert isinstance(content, str)
    assert len(content) > 0


def test_load_builtin_standup():
    """Load the built-in standup template without error."""
    from mcp_cronos.template_loader import load_template

    content = load_template("standup")
    assert isinstance(content, str)
    assert len(content) > 0


def test_load_builtin_consolida():
    """Load the built-in consolida template without error."""
    from mcp_cronos.template_loader import load_template

    content = load_template("consolida")
    assert isinstance(content, str)
    assert len(content) > 0


# ---------------------------------------------------------------------------
# fine_giornata placeholder and section presence
# ---------------------------------------------------------------------------


def test_fine_giornata_contains_blockers_placeholder():
    """The closure template must keep the blockers placeholder for config substitution."""
    from mcp_cronos.template_loader import load_template

    content = load_template("fine_giornata")
    assert "{section_blockers}" in content


@pytest.mark.parametrize(
    "section_marker",
    [
        "## Riassunto",
        "## Numeri salienti",
        "## Decisioni prese",
        "## Punti aperti",
        "## Per riprendere il lavoro",
        "## Discorso per lo standup",
        "## Domande probabili e risposte pronte",
    ],
)
def test_fine_giornata_contains_required_sections(section_marker: str):
    """The slim closure template must declare all the canonical sections."""
    from mcp_cronos.template_loader import load_template

    content = load_template("fine_giornata")
    assert section_marker in content, f"Missing section: {section_marker}"


# ---------------------------------------------------------------------------
# User override
# ---------------------------------------------------------------------------


def test_user_override_takes_precedence(tmp_diario: Path):
    """A template file in {CRONOS_DIARIO_PATH}/templates/ overrides the built-in."""
    from mcp_cronos.template_loader import load_template

    templates_dir = tmp_diario / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    override_content = "# Custom standup template\nDo something different."
    (templates_dir / "standup.md").write_text(override_content, encoding="utf-8")

    content = load_template("standup")
    assert content == override_content


def test_user_override_fine_giornata(tmp_diario: Path):
    """User override works for fine_giornata template."""
    from mcp_cronos.template_loader import load_template

    templates_dir = tmp_diario / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    override_content = "My custom fine_giornata instructions."
    (templates_dir / "fine_giornata.md").write_text(override_content, encoding="utf-8")

    content = load_template("fine_giornata")
    assert content == override_content


def test_builtin_used_when_no_override(tmp_diario: Path):
    """Built-in is returned when the override file does not exist."""
    from mcp_cronos.template_loader import load_template

    # tmp_diario exists but has no templates/ subdir
    builtin = load_template("consolida")
    assert "CONSOLIDAMENTO" in builtin or len(builtin) > 50


# ---------------------------------------------------------------------------
# Unknown template name
# ---------------------------------------------------------------------------


def test_unknown_template_raises(tmp_diario: Path):
    """Requesting an unknown template name raises FileNotFoundError."""
    from mcp_cronos.template_loader import load_template

    with pytest.raises(FileNotFoundError):
        load_template("nonexistent_template")


def test_unknown_template_raises_without_diario(monkeypatch: pytest.MonkeyPatch):
    """FileNotFoundError is raised for unknown names even when CRONOS_DIARIO_PATH is unset."""
    monkeypatch.delenv("CRONOS_DIARIO_PATH", raising=False)
    from mcp_cronos.template_loader import load_template

    with pytest.raises(FileNotFoundError):
        load_template("bad_name")
