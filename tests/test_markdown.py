"""
Tests for mcp_cronos.utils.markdown.

Covers: parse_diary_content with Italian and English section names, and
extract_projects H3 parsing and deduplication.
"""

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.utils.markdown import (
    DiaryFile,
    extract_projects,
    parse_diary_content,
    parse_entries,
)

# ---------------------------------------------------------------------------
# Autouse fixture: reset config singleton before and after each test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Reset the config singleton before and after every test to prevent state leakage."""
    _reset_config()
    yield
    _reset_config()


# ---------------------------------------------------------------------------
# Sample content helpers
# ---------------------------------------------------------------------------

_ITALIAN_DIARY = """\
# Per lo Stand-up - 9 Aprile 2026

## Cosa ho fatto ieri

### ProjectA - Fixed the login bug

Investigated session handling.

---

### ProjectB - Added caching layer

Improved response time.

---

## Bloccanti

Nessuno
"""

_ITALIAN_DIARY_VARIANT = """\
# Per lo Stand-up - 9 Aprile 2026

## Cosa ho fatto ieri e stamattina

### ProjectA - Task uno

Content.

---

## Bloccanti

Deploy bloccato per infra.
"""

_ENGLISH_DIARY = """\
# For Stand-up - April 9, 2026

## What I did yesterday

### ProjectX - Refactored auth module

Cleaned up token validation logic.

---

## Blockers

None
"""


# ---------------------------------------------------------------------------
# TestParseDiaryContentItalian
# ---------------------------------------------------------------------------


class TestParseDiaryContentItalian:
    """parse_diary_content with default Italian section names."""

    def test_parses_title(self, tmp_diario):
        """Title (H1) is extracted correctly from Italian diary content."""
        result = parse_diary_content(_ITALIAN_DIARY)
        assert result.titolo == "Per lo Stand-up - 9 Aprile 2026"

    def test_parses_entries(self, tmp_diario):
        """Entries under '## Cosa ho fatto ieri' are parsed into DiaryEntry objects."""
        result = parse_diary_content(_ITALIAN_DIARY)
        assert isinstance(result.entries, list)
        assert len(result.entries) == 2
        projects = [e.progetto for e in result.entries]
        assert "ProjectA" in projects
        assert "ProjectB" in projects

    def test_parses_blockers(self, tmp_diario):
        """Blockers text under '## Bloccanti' is extracted correctly."""
        result = parse_diary_content(_ITALIAN_DIARY)
        assert result.bloccanti == "Nessuno"

    def test_parses_blockers_non_default(self, tmp_diario):
        """Non-default blocker text is preserved as-is."""
        result = parse_diary_content(_ITALIAN_DIARY_VARIANT)
        assert result.bloccanti == "Deploy bloccato per infra."

    def test_section_entries_prefix_match(self, tmp_diario):
        """Section starting with '## Cosa ho fatto' (any suffix) is treated as entries."""
        result = parse_diary_content(_ITALIAN_DIARY_VARIANT)
        assert len(result.entries) == 1
        assert result.entries[0].progetto == "ProjectA"

    def test_returns_diary_file_instance(self, tmp_diario):
        """parse_diary_content always returns a DiaryFile instance."""
        result = parse_diary_content(_ITALIAN_DIARY)
        assert isinstance(result, DiaryFile)

    def test_empty_content_returns_defaults(self, tmp_diario):
        """Empty content returns a DiaryFile with empty title and no entries."""
        result = parse_diary_content("")
        assert result.titolo == ""
        assert result.entries == []


# ---------------------------------------------------------------------------
# TestParseDiaryContentEnglish
# ---------------------------------------------------------------------------


class TestParseDiaryContentEnglish:
    """parse_diary_content with English section names loaded from cronos.toml."""

    def test_parses_english_sections(self, tmp_diario, config_toml_en):
        """Entries and blockers are parsed correctly when lang='en' is configured."""
        result = parse_diary_content(_ENGLISH_DIARY)

        assert result.titolo == "For Stand-up - April 9, 2026"
        assert len(result.entries) == 1
        assert result.entries[0].progetto == "ProjectX"
        assert result.entries[0].descrizione == "Refactored auth module"
        assert result.bloccanti == "None"

    def test_english_blockers_default(self, tmp_diario, config_toml_en):
        """When blockers section is absent, blockers_default comes from the English pack."""
        content_no_blockers = """\
# For Stand-up - April 9, 2026

## What I did yesterday

### ProjectX - Some work

Details.

---
"""
        result = parse_diary_content(content_no_blockers)
        # blockers_default for English is "None"
        assert result.bloccanti == "None"

    def test_italian_sections_ignored_in_english_mode(self, tmp_diario, config_toml_en):
        """Italian section names are not recognised when lang='en'."""
        result = parse_diary_content(_ITALIAN_DIARY)
        # No recognised entries or blockers section for English
        assert result.entries == []


# ---------------------------------------------------------------------------
# TestExtractProjects
# ---------------------------------------------------------------------------


class TestExtractProjects:
    """extract_projects reads project names from H3 headers."""

    def test_extracts_from_h3(self, tmp_diario):
        """Project names are extracted from '### Project - Description' headers."""
        content = "### Alpha - First task\n\n### Beta - Second task\n"
        projects = extract_projects(content)
        assert "Alpha" in projects
        assert "Beta" in projects

    def test_no_duplicates(self, tmp_diario):
        """Duplicate project names are not included more than once."""
        content = "### Alpha - Task one\n\n### Alpha - Task two\n"
        projects = extract_projects(content)
        assert projects.count("Alpha") == 1

    def test_h3_without_description(self, tmp_diario):
        """A H3 header without a ' - ' separator yields the full header as project name."""
        content = "### StandaloneProject\n"
        projects = extract_projects(content)
        assert "StandaloneProject" in projects

    def test_non_h3_lines_ignored(self, tmp_diario):
        """Lines that are not H3 headers do not contribute project names."""
        content = "# Title\n## Section\n- bullet\nplain text\n"
        projects = extract_projects(content)
        assert projects == []


def test_parse_entries_ignores_headings_inside_code_fence():
    """A fenced code block containing a line starting with '### ' or a '---'
    line must not be parsed as a new entry or as an entry terminator.

    Guards the invariant that fenced content is opaque to entry segmentation.
    """
    content = (
        "### MCP Cronos - Refactor parser\n\n"
        "Intro paragraph.\n\n"
        "```bash\n"
        "### this is a shell comment, not a heading\n"
        "echo hello\n"
        "---\n"
        "echo world\n"
        "```\n\n"
        "Closing paragraph.\n"
    )

    entries = parse_entries(content)

    assert len(entries) == 1
    assert entries[0].progetto == "MCP Cronos"
    assert entries[0].descrizione == "Refactor parser"
    assert "echo hello" in entries[0].contenuto
    assert "echo world" in entries[0].contenuto
    assert "Closing paragraph." in entries[0].contenuto


def test_parse_entries_handles_nested_markdown_fences():
    """A four-backtick fence wrapping markdown that contains a three-backtick
    block must stay open across the inner fence, so a '### ' line inside the
    outer fence is not parsed as a new entry."""
    content = (
        "### Cronos - Document fence fix\n\n"
        "````markdown\n"
        "```python\n"
        "### class definition, not a heading\n"
        "x = 1\n"
        "```\n"
        "````\n\n"
        "Rest of entry.\n"
    )

    entries = parse_entries(content)

    assert len(entries) == 1
    assert entries[0].progetto == "Cronos"
    assert "class definition" in entries[0].contenuto
    assert "Rest of entry." in entries[0].contenuto


def test_render_entry_uses_configured_labels_en(tmp_diario, config_toml_en):
    from mcp_cronos.utils.markdown import DiaryEntry, render_entry

    entry = DiaryEntry(
        progetto="MCP Cronos",
        descrizione="Localise labels",
        contenuto="Body text.",
        richiesto_da="Marco",
        riferimenti={"repository": "mcp-cronos"},
    )
    rendered = render_entry(entry)

    assert "*-Requested by Marco-*" in rendered
    assert "**References:**" in rendered
    assert "Riferimenti" not in rendered
    assert "Richiesto da" not in rendered
