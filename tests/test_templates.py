"""
Tests for the templates module.

Covers: Entry.to_markdown, DiarioGiornaliero.titolo, DiarioGiornaliero.to_markdown,
and crea_template_vuoto — including language-sensitive rendering via config.
"""

from datetime import date

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.templates import (
    DiarioGiornaliero,
    Entry,
    Riferimento,
    crea_template_vuoto,
)

# ---------------------------------------------------------------------------
# Autouse fixture: reset config singleton before and after each test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_config():
    """Reset the config singleton before and after every test to prevent state leakage."""
    _reset_config()
    yield
    _reset_config()


# ---------------------------------------------------------------------------
# TestEntryToMarkdown
# ---------------------------------------------------------------------------


class TestEntryToMarkdown:
    """Tests for Entry.to_markdown."""

    def test_basic_entry(self, tmp_diario):
        """A minimal entry renders H3 header, intro paragraph, no references."""
        entry = Entry(
            progetto="Cronos",
            descrizione="Aggiunta funzionalita config",
            paragrafo_intro="Implementata la lettura del file cronos.toml.",
        )
        md = entry.to_markdown()

        assert "### Cronos - Aggiunta funzionalita config" in md
        assert "Implementata la lettura del file cronos.toml." in md
        assert "**Riferimenti:**" not in md
        assert "*-Richiesto da" not in md

    def test_with_riferimenti(self, tmp_diario):
        """An entry with references renders the Riferimenti block correctly."""
        entry = Entry(
            progetto="Backend",
            descrizione="Fix autenticazione",
            paragrafo_intro="Corretto il bug nel token refresh.",
            riferimenti=[
                Riferimento(tipo="branch", valore="fix/auth-token", url=None),
                Riferimento(tipo="jira", valore="BACK-42", url="https://jira.example.com/BACK-42"),
            ],
        )
        md = entry.to_markdown()

        assert "**Riferimenti:**" in md
        assert "- Branch: `fix/auth-token`" in md
        assert "- Jira: [BACK-42](https://jira.example.com/BACK-42)" in md

    def test_with_richiesto_da(self, tmp_diario):
        """An entry with richiesto_da includes the attribution line."""
        entry = Entry(
            progetto="Infra",
            descrizione="Aggiornamento dipendenze",
            paragrafo_intro="Aggiornate tutte le dipendenze al minor piu recente.",
            richiesto_da="Team Platform",
        )
        md = entry.to_markdown()

        assert "*-Richiesto da Team Platform-*" in md

    def test_with_contenuto(self, tmp_diario):
        """An entry with contenuto includes the extra content block."""
        entry = Entry(
            progetto="API",
            descrizione="Endpoint nuovo",
            paragrafo_intro="Aggiunto endpoint GET /status.",
            contenuto="Il servizio risponde 200 OK con payload JSON.",
        )
        md = entry.to_markdown()

        assert "Il servizio risponde 200 OK con payload JSON." in md


# ---------------------------------------------------------------------------
# TestDiarioGiornaliero
# ---------------------------------------------------------------------------


class TestDiarioGiornaliero:
    """Tests for DiarioGiornaliero.titolo and DiarioGiornaliero.to_markdown."""

    def test_italian_title(self, tmp_diario):
        """titolo uses the Italian prefix and date format by default (no config file)."""
        diario = DiarioGiornaliero(data=date(2026, 4, 9))
        # standup date is 2026-04-10
        assert "Per lo Stand-up" in diario.titolo
        assert "Aprile" in diario.titolo
        assert "2026" in diario.titolo

    def test_english_title(self, config_toml_en):
        """titolo uses the English prefix and date format when lang='en'."""
        diario = DiarioGiornaliero(data=date(2026, 4, 9))
        # standup date is 2026-04-10
        assert "For Stand-up" in diario.titolo
        assert "April" in diario.titolo
        assert "2026" in diario.titolo

    def test_to_markdown_has_sections_italian(self, tmp_diario):
        """to_markdown renders Italian section headers when no config file is present."""
        diario = DiarioGiornaliero(data=date(2026, 4, 9))
        md = diario.to_markdown()

        assert "## Cosa ho fatto ieri" in md
        assert "## Bloccanti" in md

    def test_to_markdown_english_sections(self, config_toml_en):
        """to_markdown renders English section headers when lang='en'."""
        diario = DiarioGiornaliero(data=date(2026, 4, 9), bloccanti="None")
        md = diario.to_markdown()

        assert "## What I did yesterday" in md
        assert "## Blockers" in md

    def test_to_markdown_contains_title(self, tmp_diario):
        """to_markdown starts with an H1 line containing the standup title."""
        diario = DiarioGiornaliero(data=date(2026, 4, 9))
        md = diario.to_markdown()

        first_line = md.splitlines()[0]
        assert first_line.startswith("# ")
        assert "Per lo Stand-up" in first_line

    def test_to_markdown_includes_bloccanti(self, tmp_diario):
        """to_markdown renders the bloccanti value in the blockers section."""
        diario = DiarioGiornaliero(data=date(2026, 4, 9), bloccanti="Deploy bloccato")
        md = diario.to_markdown()

        assert "Deploy bloccato" in md

    def test_to_markdown_with_entry(self, tmp_diario):
        """to_markdown renders entry content and the horizontal rule separator."""
        entry = Entry(
            progetto="Cronos",
            descrizione="Test",
            paragrafo_intro="Aggiunto il modulo config.",
        )
        diario = DiarioGiornaliero(data=date(2026, 4, 9))
        diario.aggiungi_entry(entry)
        md = diario.to_markdown()

        assert "### Cronos - Test" in md
        assert "---" in md


# ---------------------------------------------------------------------------
# TestCreaTemplateVuoto
# ---------------------------------------------------------------------------


class TestCreaTemplateVuoto:
    """Tests for crea_template_vuoto."""

    def test_italian_template(self, tmp_diario):
        """crea_template_vuoto uses Italian section names and blockers default by default."""
        result = crea_template_vuoto(date(2026, 4, 9))

        assert "## Cosa ho fatto ieri" in result
        assert "## Bloccanti" in result
        assert "Nessuno" in result

    def test_english_template(self, config_toml_en):
        """crea_template_vuoto uses English section names and blockers default when lang='en'."""
        result = crea_template_vuoto(date(2026, 4, 9))

        assert "## What I did yesterday" in result
        assert "## Blockers" in result
        assert "None" in result

    def test_template_starts_with_title(self, tmp_diario):
        """crea_template_vuoto generates a string that starts with an H1 title."""
        result = crea_template_vuoto(date(2026, 4, 9))
        first_line = result.splitlines()[0]

        assert first_line.startswith("# ")
        assert "Per lo Stand-up" in first_line

    def test_template_english_title(self, config_toml_en):
        """crea_template_vuoto generates an English title when lang='en'."""
        result = crea_template_vuoto(date(2026, 4, 9))
        first_line = result.splitlines()[0]

        assert "For Stand-up" in first_line
        assert "April" in first_line

    def test_template_ends_with_newline(self, tmp_diario):
        """crea_template_vuoto output ends with a trailing newline."""
        result = crea_template_vuoto(date(2026, 4, 9))
        assert result.endswith("\n")


def test_entry_to_markdown_skips_empty_intro():
    from mcp_cronos.templates import Entry

    md = Entry(progetto="P", descrizione="D", paragrafo_intro="").to_markdown()
    assert md.startswith("### P - D")
    assert "\n\n\n" not in md
