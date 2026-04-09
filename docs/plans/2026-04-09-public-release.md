# mcp-cronos Public Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make mcp-cronos a publishable PyPI package with full i18n, configurable templates, test suite, and bilingual documentation.

**Architecture:** Add a configuration layer (`config.py` + `cronos.toml`) and i18n module (`i18n.py`) that feed language-aware values to all existing tools. Externalize LLM prompt templates to `default_templates/`. Replace all hardcoded Italian strings with config/i18n lookups. Add comprehensive test suite. Update pyproject.toml for PyPI.

**Tech Stack:** Python 3.10+ | MCP SDK | Pydantic 2.x | tomli/tomllib (TOML parsing) | pytest + pytest-asyncio

**Spec:** `docs/specs/2026-04-09-public-release-design.md`

---

### Task 1: Add tomli dependency and test infrastructure

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Update pyproject.toml with tomli dependency and test config**

```toml
# Add to [project] dependencies:
dependencies = [
    "mcp>=1.0.0",
    "pydantic>=2.0.0",
    "tomli>=2.0.0; python_version < '3.11'",
]
```

- [ ] **Step 2: Create tests directory and conftest**

Create `tests/__init__.py` (empty).

Create `tests/conftest.py`:

```python
"""Shared test fixtures for mcp-cronos."""

import os
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def tmp_diario(tmp_path):
    """Create a temporary diary directory structure."""
    diario = tmp_path / "Diario"
    diario.mkdir()
    with patch.dict(os.environ, {"CRONOS_DIARIO_PATH": str(diario)}):
        yield diario


@pytest.fixture
def sample_diary_it(tmp_diario):
    """Create a sample Italian diary file for 2026-04-09."""
    day_dir = tmp_diario / "2026" / "04"
    day_dir.mkdir(parents=True)
    file_path = day_dir / "2026-04-09.md"
    file_path.write_text(
        "# Per lo Stand-up 10 Aprile 2026\n"
        "\n"
        "## Cosa ho fatto ieri\n"
        "\n"
        "### TestProject - Fix bug login\n"
        "\n"
        "Fixed the authentication flow.\n"
        "\n"
        "**Riferimenti:**\n"
        "- Repository: test-repo\n"
        "- Branch: `fix/login`\n"
        "\n"
        "---\n"
        "\n"
        "## Bloccanti\n"
        "\n"
        "Nessuno\n",
        encoding="utf-8",
    )
    return file_path


@pytest.fixture
def sample_diary_en(tmp_diario):
    """Create a sample English diary file for 2026-04-09."""
    day_dir = tmp_diario / "2026" / "04"
    day_dir.mkdir(parents=True)
    file_path = day_dir / "2026-04-09.md"
    file_path.write_text(
        "# For Stand-up April 10, 2026\n"
        "\n"
        "## What I did yesterday\n"
        "\n"
        "### TestProject - Fix login bug\n"
        "\n"
        "Fixed the authentication flow.\n"
        "\n"
        "---\n"
        "\n"
        "## Blockers\n"
        "\n"
        "None\n",
        encoding="utf-8",
    )
    return file_path


@pytest.fixture
def config_toml_it(tmp_diario):
    """Create a cronos.toml with Italian config in the diary root."""
    config_path = tmp_diario / "cronos.toml"
    config_path.write_text(
        '[cronos]\n'
        'lang = "it"\n'
        '\n'
        '[cronos.git]\n'
        'enabled = false\n',
        encoding="utf-8",
    )
    return config_path


@pytest.fixture
def config_toml_en(tmp_diario):
    """Create a cronos.toml with English config in the diary root."""
    config_path = tmp_diario / "cronos.toml"
    config_path.write_text(
        '[cronos]\n'
        'lang = "en"\n'
        '\n'
        '[cronos.git]\n'
        'enabled = false\n',
        encoding="utf-8",
    )
    return config_path
```

- [ ] **Step 3: Run uv sync to install dependencies**

Run: `uv sync`
Expected: Dependencies installed including tomli.

- [ ] **Step 4: Verify pytest runs (no tests yet)**

Run: `uv run pytest --co`
Expected: "no tests ran" or empty collection, no import errors.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/ uv.lock
git commit -m "chore: add tomli dependency and test infrastructure"
```

---

### Task 2: Implement i18n module

**Files:**
- Create: `src/mcp_cronos/i18n.py`
- Create: `tests/test_i18n.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_i18n.py`:

```python
"""Tests for the i18n module."""

from mcp_cronos.i18n import LanguagePack, get_language_pack, LANGUAGES


class TestLanguagePack:
    def test_italian_is_registered(self):
        assert "it" in LANGUAGES

    def test_english_is_registered(self):
        assert "en" in LANGUAGES

    def test_italian_months_count(self):
        pack = LANGUAGES["it"]
        assert len(pack.months) == 12

    def test_english_months_count(self):
        pack = LANGUAGES["en"]
        assert len(pack.months) == 12

    def test_italian_weekdays_count(self):
        pack = LANGUAGES["it"]
        assert len(pack.weekdays) == 7

    def test_italian_has_all_sections(self):
        pack = LANGUAGES["it"]
        assert "entries" in pack.sections
        assert "blockers" in pack.sections
        assert "day_summary" in pack.sections
        assert "tech_summary" in pack.sections
        assert "standup_message" in pack.sections

    def test_english_has_all_sections(self):
        pack = LANGUAGES["en"]
        assert "entries" in pack.sections
        assert "blockers" in pack.sections

    def test_italian_months_start_with_gennaio(self):
        pack = LANGUAGES["it"]
        assert pack.months[0] == "Gennaio"

    def test_english_months_start_with_january(self):
        pack = LANGUAGES["en"]
        assert pack.months[0] == "January"

    def test_italian_title_prefix(self):
        pack = LANGUAGES["it"]
        assert pack.title_prefix == "Per lo Stand-up"

    def test_english_title_prefix(self):
        pack = LANGUAGES["en"]
        assert pack.title_prefix == "For Stand-up"


class TestGetLanguagePack:
    def test_get_italian(self):
        pack = get_language_pack("it")
        assert pack.months[0] == "Gennaio"

    def test_get_english(self):
        pack = get_language_pack("en")
        assert pack.months[0] == "January"

    def test_unknown_language_falls_back_to_italian(self):
        pack = get_language_pack("xx")
        assert pack.months[0] == "Gennaio"

    def test_format_date_italian(self):
        from datetime import date
        pack = get_language_pack("it")
        d = date(2026, 4, 10)
        result = pack.format_date(d)
        assert result == "10 Aprile 2026"

    def test_format_date_english(self):
        from datetime import date
        pack = get_language_pack("en")
        d = date(2026, 4, 10)
        result = pack.format_date(d)
        assert result == "April 10, 2026"

    def test_format_title_italian(self):
        from datetime import date
        pack = get_language_pack("it")
        d = date(2026, 4, 9)
        # Standup title uses day+1
        standup_date = date(2026, 4, 10)
        result = pack.format_title(standup_date)
        assert result == "Per lo Stand-up 10 Aprile 2026"

    def test_format_title_english(self):
        from datetime import date
        pack = get_language_pack("en")
        standup_date = date(2026, 4, 10)
        result = pack.format_title(standup_date)
        assert result == "For Stand-up April 10, 2026"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_i18n.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement i18n module**

Create `src/mcp_cronos/i18n.py`:

```python
"""
Internationalization support for mcp-cronos.

Provides language packs with month names, weekday names, section titles,
and date formatting for diary generation and parsing.

Built-in languages: Italian (it, default), English (en).
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class LanguagePack:
    """Language-specific strings and formatting rules for diary content."""

    code: str
    months: list[str]
    weekdays: list[str]
    title_prefix: str
    date_format: str  # Python-style with {day}, {month}, {year}
    sections: dict[str, str]
    blockers_default: str
    temporal: dict[str, str] = field(default_factory=dict)

    def format_date(self, d: date) -> str:
        """Format a date using this language's date format."""
        month_name = self.months[d.month - 1]
        return self.date_format.format(day=d.day, month=month_name, year=d.year)

    def format_title(self, standup_date: date) -> str:
        """Format the standup title for the given date."""
        formatted_date = self.format_date(standup_date)
        return f"{self.title_prefix} {formatted_date}"


LANGUAGES: dict[str, LanguagePack] = {
    "it": LanguagePack(
        code="it",
        months=[
            "Gennaio", "Febbraio", "Marzo", "Aprile",
            "Maggio", "Giugno", "Luglio", "Agosto",
            "Settembre", "Ottobre", "Novembre", "Dicembre",
        ],
        weekdays=[
            "lunedi", "martedi", "mercoledi", "giovedi",
            "venerdi", "sabato", "domenica",
        ],
        title_prefix="Per lo Stand-up",
        date_format="{day} {month} {year}",
        sections={
            "entries": "Cosa ho fatto ieri",
            "blockers": "Bloccanti",
            "day_summary": "Riassunto della giornata",
            "tech_summary": "Riassunto tecnico",
            "standup_message": "Messaggio per lo standup",
        },
        blockers_default="Nessuno",
        temporal={
            "yesterday": "Ieri",
            "day_before": "L'altro ieri",
            "last_weekday": "{weekday} scorso",
            "from_to": "Dal {start} al {end}",
        },
    ),
    "en": LanguagePack(
        code="en",
        months=[
            "January", "February", "March", "April",
            "May", "June", "July", "August",
            "September", "October", "November", "December",
        ],
        weekdays=[
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ],
        title_prefix="For Stand-up",
        date_format="{month} {day}, {year}",
        sections={
            "entries": "What I did yesterday",
            "blockers": "Blockers",
            "day_summary": "Daily summary",
            "tech_summary": "Technical summary",
            "standup_message": "Standup message",
        },
        blockers_default="None",
        temporal={
            "yesterday": "Yesterday",
            "day_before": "Day before yesterday",
            "last_weekday": "Last {weekday}",
            "from_to": "From {start} to {end}",
        },
    ),
}


def get_language_pack(lang: str) -> LanguagePack:
    """
    Get the language pack for the given language code.

    Falls back to Italian if the language is not found.

    Args:
        lang: Language code (e.g., "it", "en")

    Returns:
        LanguagePack for the requested language
    """
    return LANGUAGES.get(lang, LANGUAGES["it"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_i18n.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/mcp_cronos/i18n.py tests/test_i18n.py
git commit -m "feat(i18n): add language pack system with Italian and English support"
```

---

### Task 3: Implement configuration system

**Files:**
- Modify: `src/mcp_cronos/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config.py`:

```python
"""Tests for the configuration module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_cronos.config import get_diario_path, load_config, CronosConfig, _reset_config


@pytest.fixture(autouse=True)
def reset_config_cache():
    """Reset the config singleton before each test."""
    _reset_config()
    yield
    _reset_config()


class TestGetDiarioPath:
    def test_returns_path_from_env(self, tmp_path):
        with patch.dict(os.environ, {"CRONOS_DIARIO_PATH": str(tmp_path)}):
            assert get_diario_path() == tmp_path

    def test_raises_without_env(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CRONOS_DIARIO_PATH", None)
            with pytest.raises(RuntimeError, match="CRONOS_DIARIO_PATH"):
                get_diario_path()


class TestLoadConfig:
    def test_default_config_without_file(self, tmp_diario):
        config = load_config()
        assert config.lang == "it"
        assert config.git_enabled is True
        assert config.auto_push is True

    def test_loads_from_diario_root(self, tmp_diario):
        config_file = tmp_diario / "cronos.toml"
        config_file.write_text('[cronos]\nlang = "en"\n', encoding="utf-8")
        config = load_config()
        assert config.lang == "en"

    def test_loads_from_explicit_path(self, tmp_diario, tmp_path):
        config_file = tmp_path / "custom.toml"
        config_file.write_text('[cronos]\nlang = "en"\n', encoding="utf-8")
        with patch.dict(os.environ, {"CRONOS_CONFIG_PATH": str(config_file)}):
            _reset_config()
            config = load_config()
            assert config.lang == "en"

    def test_section_names_from_language(self, tmp_diario):
        config = load_config()
        assert config.section_entries == "Cosa ho fatto ieri"
        assert config.section_blockers == "Bloccanti"

    def test_section_names_english(self, tmp_diario):
        config_file = tmp_diario / "cronos.toml"
        config_file.write_text('[cronos]\nlang = "en"\n', encoding="utf-8")
        config = load_config()
        assert config.section_entries == "What I did yesterday"
        assert config.section_blockers == "Blockers"

    def test_section_override_in_config(self, tmp_diario):
        config_file = tmp_diario / "cronos.toml"
        config_file.write_text(
            '[cronos]\nlang = "it"\n\n'
            '[cronos.sections]\n'
            'entries = "Attivita svolte"\n',
            encoding="utf-8",
        )
        config = load_config()
        assert config.section_entries == "Attivita svolte"
        assert config.section_blockers == "Bloccanti"  # not overridden

    def test_git_config(self, tmp_diario):
        config_file = tmp_diario / "cronos.toml"
        config_file.write_text(
            '[cronos.git]\n'
            'enabled = false\n'
            'auto_push = false\n'
            'commit_message = "diary: {date}"\n',
            encoding="utf-8",
        )
        config = load_config()
        assert config.git_enabled is False
        assert config.auto_push is False
        assert config.commit_message == "diary: {date}"

    def test_default_git_commit_message(self, tmp_diario):
        config = load_config()
        assert config.commit_message == "diario: fine giornata {date}"

    def test_invalid_toml_falls_back_to_defaults(self, tmp_diario):
        config_file = tmp_diario / "cronos.toml"
        config_file.write_text("this is not valid toml [[[", encoding="utf-8")
        config = load_config()
        assert config.lang == "it"

    def test_blockers_default_from_language(self, tmp_diario):
        config = load_config()
        assert config.blockers_default == "Nessuno"

    def test_blockers_default_english(self, tmp_diario):
        config_file = tmp_diario / "cronos.toml"
        config_file.write_text('[cronos]\nlang = "en"\n', encoding="utf-8")
        config = load_config()
        assert config.blockers_default == "None"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL (CronosConfig not found)

- [ ] **Step 3: Implement the config module**

Replace `src/mcp_cronos/config.py` with:

```python
"""
Configuration for mcp-cronos.

Loads settings from cronos.toml (searched in diary root, ~/.config/cronos/,
or explicit CRONOS_CONFIG_PATH). Falls back to language-specific defaults.

Config priority: user config > language defaults > Italian defaults.
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from mcp_cronos.i18n import get_language_pack

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore[assignment]


@dataclass
class CronosConfig:
    """Resolved configuration for mcp-cronos."""

    lang: str
    section_entries: str
    section_blockers: str
    section_day_summary: str
    section_tech_summary: str
    section_standup_message: str
    blockers_default: str
    title_format: str  # e.g. "{prefix} {date}"
    git_enabled: bool
    auto_push: bool
    commit_message: str


# Singleton cache
_config: Optional[CronosConfig] = None


def _reset_config() -> None:
    """Reset the cached config. Used in tests."""
    global _config
    _config = None


def get_diario_path() -> Path:
    """
    Return the diary root path from CRONOS_DIARIO_PATH env var.

    Raises:
        RuntimeError: If CRONOS_DIARIO_PATH is not set
    """
    path_str = os.environ.get("CRONOS_DIARIO_PATH")
    if not path_str:
        raise RuntimeError(
            "Variabile d'ambiente CRONOS_DIARIO_PATH non impostata. "
            "Imposta il path del diario di lavoro, es: "
            "CRONOS_DIARIO_PATH=/path/to/Diario"
        )
    return Path(path_str)


def ensure_diario_exists() -> bool:
    """Check if the diary path exists."""
    return get_diario_path().exists()


def _find_config_file() -> Optional[Path]:
    """
    Search for cronos.toml in standard locations.

    Search order:
    1. CRONOS_CONFIG_PATH env var (explicit)
    2. {CRONOS_DIARIO_PATH}/cronos.toml
    3. ~/.config/cronos/cronos.toml
    """
    explicit = os.environ.get("CRONOS_CONFIG_PATH")
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p

    try:
        diario = get_diario_path()
        candidate = diario / "cronos.toml"
        if candidate.is_file():
            return candidate
    except RuntimeError:
        pass

    home_config = Path.home() / ".config" / "cronos" / "cronos.toml"
    if home_config.is_file():
        return home_config

    return None


def _parse_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file, returning empty dict on error."""
    if tomllib is None:
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def load_config() -> CronosConfig:
    """
    Load and cache the configuration.

    Merges user config with language defaults. Returns cached instance
    on subsequent calls.
    """
    global _config
    if _config is not None:
        return _config

    config_file = _find_config_file()
    raw = _parse_toml(config_file) if config_file else {}

    cronos = raw.get("cronos", {})
    lang = cronos.get("lang", "it")
    pack = get_language_pack(lang)

    # Sections: user overrides > language defaults
    sections_raw = cronos.get("sections", {})
    section_entries = sections_raw.get("entries", pack.sections["entries"])
    section_blockers = sections_raw.get("blockers", pack.sections["blockers"])
    section_day_summary = sections_raw.get("day_summary", pack.sections["day_summary"])
    section_tech_summary = sections_raw.get("tech_summary", pack.sections["tech_summary"])
    section_standup_message = sections_raw.get("standup_message", pack.sections["standup_message"])
    blockers_default = sections_raw.get("blockers_default", pack.blockers_default)

    # Diary formatting
    diary_raw = cronos.get("diary", {})
    title_format = diary_raw.get("title_format", "{prefix} {date}")

    # Git
    git_raw = cronos.get("git", {})
    git_enabled = git_raw.get("enabled", True)
    auto_push = git_raw.get("auto_push", True)
    commit_message = git_raw.get("commit_message", "diario: fine giornata {date}")

    _config = CronosConfig(
        lang=lang,
        section_entries=section_entries,
        section_blockers=section_blockers,
        section_day_summary=section_day_summary,
        section_tech_summary=section_tech_summary,
        section_standup_message=section_standup_message,
        blockers_default=blockers_default,
        title_format=title_format,
        git_enabled=git_enabled,
        auto_push=auto_push,
        commit_message=commit_message,
    )
    return _config
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py tests/test_i18n.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/mcp_cronos/config.py tests/test_config.py
git commit -m "feat(config): add TOML config system with language-aware defaults"
```

---

### Task 4: Externalize LLM templates

**Files:**
- Create: `src/mcp_cronos/default_templates/fine_giornata.md`
- Create: `src/mcp_cronos/default_templates/standup.md`
- Create: `src/mcp_cronos/default_templates/consolida.md`
- Create: `src/mcp_cronos/template_loader.py`
- Create: `tests/test_template_loader.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_template_loader.py`:

```python
"""Tests for template loading."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_cronos.template_loader import load_template
from mcp_cronos.config import _reset_config


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestLoadTemplate:
    def test_loads_builtin_fine_giornata(self):
        template = load_template("fine_giornata")
        assert len(template) > 100
        assert "{section_entries}" in template

    def test_loads_builtin_standup(self):
        template = load_template("standup")
        assert len(template) > 100

    def test_loads_builtin_consolida(self):
        template = load_template("consolida")
        assert len(template) > 100

    def test_user_override_from_diario(self, tmp_diario):
        templates_dir = tmp_diario / "templates"
        templates_dir.mkdir()
        custom = templates_dir / "standup.md"
        custom.write_text("Custom standup template", encoding="utf-8")
        result = load_template("standup")
        assert result == "Custom standup template"

    def test_unknown_template_raises(self):
        with pytest.raises(FileNotFoundError):
            load_template("nonexistent")

    def test_section_placeholders_replaced(self):
        template = load_template("fine_giornata")
        # After loading, placeholders should still be present
        # (they are replaced at call site, not at load time)
        assert "{section_entries}" in template
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_template_loader.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Extract current templates to files**

Create `src/mcp_cronos/default_templates/fine_giornata.md` — copy the content of `STILE_FINE_GIORNATA` from `tools/fine_giornata.py`, but replace hardcoded section names with placeholders:
- `## Cosa ho fatto ieri` -> `## {section_entries}`
- `## Bloccanti` -> `## {section_blockers}`
- `## Riassunto della giornata` -> `## {section_day_summary}`
- `## Riassunto tecnico` -> `## {section_tech_summary}`
- `## Messaggio per lo standup` -> `## {section_standup_message}`

Create `src/mcp_cronos/default_templates/standup.md` — copy `STILE_RIASSUNTO` from `tools/standup.py`.

Create `src/mcp_cronos/default_templates/consolida.md` — copy `STILE_CONSOLIDAMENTO` from `tools/consolida.py`, replacing section names with placeholders.

- [ ] **Step 4: Implement template_loader.py**

Create `src/mcp_cronos/template_loader.py`:

```python
"""
Template loader for LLM prompt templates.

Searches for user overrides in {CRONOS_DIARIO_PATH}/templates/,
falls back to built-in defaults in default_templates/.

Templates use {section_*} placeholders for i18n section names.
Placeholders are NOT resolved at load time — callers resolve them
with the current config values.
"""

from pathlib import Path
from typing import Optional

from mcp_cronos.config import get_diario_path


_BUILTIN_DIR = Path(__file__).parent / "default_templates"

_VALID_TEMPLATES = {"fine_giornata", "standup", "consolida"}


def _find_user_template(name: str) -> Optional[Path]:
    """Search for a user-provided template override."""
    try:
        diario = get_diario_path()
        candidate = diario / "templates" / f"{name}.md"
        if candidate.is_file():
            return candidate
    except RuntimeError:
        pass
    return None


def load_template(name: str) -> str:
    """
    Load an LLM prompt template by name.

    Search order:
    1. {CRONOS_DIARIO_PATH}/templates/{name}.md (user override)
    2. Built-in default_templates/{name}.md

    Args:
        name: Template name without extension (fine_giornata, standup, consolida)

    Returns:
        Template content as string

    Raises:
        FileNotFoundError: If template name is invalid or built-in is missing
    """
    if name not in _VALID_TEMPLATES:
        raise FileNotFoundError(f"Unknown template: {name}")

    user_path = _find_user_template(name)
    if user_path:
        return user_path.read_text(encoding="utf-8")

    builtin_path = _BUILTIN_DIR / f"{name}.md"
    if builtin_path.is_file():
        return builtin_path.read_text(encoding="utf-8")

    raise FileNotFoundError(f"Built-in template not found: {builtin_path}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_template_loader.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/mcp_cronos/default_templates/ src/mcp_cronos/template_loader.py tests/test_template_loader.py
git commit -m "feat(templates): externalize LLM templates with user override support"
```

---

### Task 5: Migrate dates.py to use i18n

**Files:**
- Modify: `src/mcp_cronos/utils/dates.py`
- Create: `tests/test_dates.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_dates.py`:

```python
"""Tests for date utilities."""

import os
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_cronos.config import _reset_config


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestGetStandupTitle:
    def test_italian_default(self):
        from mcp_cronos.utils.dates import get_standup_title
        result = get_standup_title(date(2026, 4, 9))
        assert result == "Per lo Stand-up 10 Aprile 2026"

    def test_english(self, config_toml_en):
        from mcp_cronos.utils.dates import get_standup_title
        result = get_standup_title(date(2026, 4, 9))
        assert result == "For Stand-up April 10, 2026"


class TestGetFilePath:
    def test_path_format(self, tmp_diario):
        from mcp_cronos.utils.dates import get_file_path
        result = get_file_path(date(2026, 4, 9))
        assert result == tmp_diario / "2026" / "04" / "2026-04-09.md"


class TestParseDate:
    def test_valid_date(self):
        from mcp_cronos.utils.dates import parse_date
        result = parse_date("2026-04-09")
        assert result == date(2026, 4, 9)

    def test_invalid_format(self):
        from mcp_cronos.utils.dates import parse_date
        with pytest.raises(ValueError, match="Formato data non valido"):
            parse_date("09-04-2026")


class TestGetDateRange:
    def test_single_day(self):
        from mcp_cronos.utils.dates import get_date_range
        result = get_date_range(date(2026, 4, 9), date(2026, 4, 9))
        assert result == [date(2026, 4, 9)]

    def test_multi_day(self):
        from mcp_cronos.utils.dates import get_date_range
        result = get_date_range(date(2026, 4, 7), date(2026, 4, 9))
        assert len(result) == 3


class TestEnsureDirectoryExists:
    def test_creates_parents(self, tmp_path):
        from mcp_cronos.utils.dates import ensure_directory_exists
        file_path = tmp_path / "a" / "b" / "file.md"
        ensure_directory_exists(file_path)
        assert file_path.parent.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_dates.py -v`
Expected: English test fails (dates.py still uses hardcoded Italian months)

- [ ] **Step 3: Update dates.py to use i18n**

In `src/mcp_cronos/utils/dates.py`:
- Remove the hardcoded `MESI_ITALIANI` list
- Import `load_config` from `mcp_cronos.config` and `get_language_pack` from `mcp_cronos.i18n`
- Update `get_standup_title` and `format_standup_date` to use the language pack from config

Key changes:

```python
from mcp_cronos.config import load_config
from mcp_cronos.i18n import get_language_pack

def format_standup_date(standup_date: date) -> str:
    config = load_config()
    pack = get_language_pack(config.lang)
    return pack.format_date(standup_date)

def get_standup_title(file_date: date) -> str:
    config = load_config()
    pack = get_language_pack(config.lang)
    standup_date = get_standup_date(file_date)
    return pack.format_title(standup_date)
```

Keep all other functions unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dates.py tests/test_i18n.py tests/test_config.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/mcp_cronos/utils/dates.py tests/test_dates.py
git commit -m "refactor(dates): use i18n language pack instead of hardcoded Italian months"
```

---

### Task 6: Migrate markdown.py to use config section names

**Files:**
- Modify: `src/mcp_cronos/utils/markdown.py`
- Create: `tests/test_markdown.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_markdown.py`:

```python
"""Tests for markdown parsing and rendering."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.utils.markdown import parse_diary_content, extract_projects


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestParseDiaryContentItalian:
    def test_parses_title(self):
        content = (
            "# Per lo Stand-up 10 Aprile 2026\n\n"
            "## Cosa ho fatto ieri\n\n"
            "### Proj - Desc\n\nContent\n\n---\n\n"
            "## Bloccanti\n\nNessuno\n"
        )
        diary = parse_diary_content(content)
        assert diary.titolo == "Per lo Stand-up 10 Aprile 2026"

    def test_parses_entries(self):
        content = (
            "# Title\n\n"
            "## Cosa ho fatto ieri\n\n"
            "### MyProject - Fix bug\n\nFixed it.\n\n---\n\n"
            "## Bloccanti\n\nNessuno\n"
        )
        diary = parse_diary_content(content)
        assert len(diary.entries) == 1
        assert diary.entries[0].progetto == "MyProject"

    def test_parses_blockers(self):
        content = (
            "# Title\n\n"
            "## Cosa ho fatto ieri\n\n"
            "## Bloccanti\n\nBlocked by API\n"
        )
        diary = parse_diary_content(content)
        assert diary.bloccanti == "Blocked by API"


class TestParseDiaryContentEnglish:
    def test_parses_english_sections(self, config_toml_en):
        content = (
            "# For Stand-up April 10, 2026\n\n"
            "## What I did yesterday\n\n"
            "### MyProject - Fix bug\n\nFixed it.\n\n---\n\n"
            "## Blockers\n\nNone\n"
        )
        diary = parse_diary_content(content)
        assert len(diary.entries) == 1
        assert diary.entries[0].progetto == "MyProject"
        assert diary.bloccanti == "None"


class TestExtractProjects:
    def test_extracts_from_h3(self):
        content = "### Alpha - task1\n\n### Beta - task2\n"
        result = extract_projects(content)
        assert result == ["Alpha", "Beta"]

    def test_no_duplicates(self):
        content = "### Alpha - task1\n\n### Alpha - task2\n"
        result = extract_projects(content)
        assert result == ["Alpha"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_markdown.py -v`
Expected: English parsing test fails (hardcoded "Cosa ho fatto" in parsing logic)

- [ ] **Step 3: Update markdown.py to use config section names**

In `src/mcp_cronos/utils/markdown.py`, update `parse_diary_content` to use config section names:

```python
from mcp_cronos.config import load_config

def parse_diary_content(content: str) -> DiaryFile:
    config = load_config()
    # ...
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"## {config.section_entries}"):
            cosa_fatto_idx = i
        elif stripped == f"## {config.section_blockers}":
            bloccanti_idx = i
    # rest unchanged
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_markdown.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/mcp_cronos/utils/markdown.py tests/test_markdown.py
git commit -m "refactor(markdown): use config section names for diary parsing"
```

---

### Task 7: Migrate templates.py to use config

**Files:**
- Modify: `src/mcp_cronos/templates.py`
- Create: `tests/test_templates.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_templates.py`:

```python
"""Tests for diary templates and data models."""

import os
from datetime import date
from unittest.mock import patch

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.templates import Entry, Riferimento, DiarioGiornaliero, crea_template_vuoto


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestEntryToMarkdown:
    def test_basic_entry(self):
        entry = Entry(progetto="Proj", descrizione="Desc", paragrafo_intro="Did stuff.")
        md = entry.to_markdown()
        assert "### Proj - Desc" in md
        assert "Did stuff." in md

    def test_with_riferimenti(self):
        entry = Entry(
            progetto="P", descrizione="D", paragrafo_intro="Intro",
            riferimenti=[Riferimento(tipo="Repository", valore="my-repo")],
        )
        md = entry.to_markdown()
        assert "**Riferimenti:**" in md
        assert "my-repo" in md


class TestDiarioGiornaliero:
    def test_italian_title(self):
        d = DiarioGiornaliero(data=date(2026, 4, 9))
        assert "Stand-up" in d.titolo
        assert "Aprile" in d.titolo

    def test_english_title(self, config_toml_en):
        d = DiarioGiornaliero(data=date(2026, 4, 9))
        assert "Stand-up" in d.titolo
        assert "April" in d.titolo

    def test_to_markdown_has_sections(self):
        d = DiarioGiornaliero(data=date(2026, 4, 9))
        md = d.to_markdown()
        assert "## Cosa ho fatto ieri" in md
        assert "## Bloccanti" in md

    def test_to_markdown_english_sections(self, config_toml_en):
        d = DiarioGiornaliero(data=date(2026, 4, 9))
        md = d.to_markdown()
        assert "## What I did yesterday" in md
        assert "## Blockers" in md


class TestCreaTemplateVuoto:
    def test_italian_template(self):
        result = crea_template_vuoto(date(2026, 4, 9))
        assert "Cosa ho fatto ieri" in result
        assert "Bloccanti" in result
        assert "Nessuno" in result

    def test_english_template(self, config_toml_en):
        result = crea_template_vuoto(date(2026, 4, 9))
        assert "What I did yesterday" in result
        assert "Blockers" in result
        assert "None" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_templates.py -v`
Expected: English tests fail

- [ ] **Step 3: Update templates.py to use config**

Update `DiarioGiornaliero.to_markdown()` and `crea_template_vuoto()` to use `load_config()` for section names and blockers default. Update imports.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_templates.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/mcp_cronos/templates.py tests/test_templates.py
git commit -m "refactor(templates): use config for section names and blockers default"
```

---

### Task 8: Migrate tool modules to use config

**Files:**
- Modify: `src/mcp_cronos/tools/entries.py`
- Modify: `src/mcp_cronos/tools/fine_giornata.py`
- Modify: `src/mcp_cronos/tools/standup.py`
- Modify: `src/mcp_cronos/tools/consolida.py`
- Modify: `src/mcp_cronos/tools/aggiungi_progetto.py`
- Modify: `src/mcp_cronos/tools/scrivi_fine_giornata.py`
- Create: `tests/test_entries.py`
- Create: `tests/test_fine_giornata.py`
- Create: `tests/test_scrivi.py`
- Create: `tests/test_standup.py`
- Create: `tests/test_consolida.py`
- Create: `tests/test_cerca.py`
- Create: `tests/test_settimana.py`
- Create: `tests/test_aggiungi_progetto.py`
- Create: `tests/test_reader.py`

This is the largest task. It should be split into sub-steps per module.

- [ ] **Step 1: Migrate entries.py — replace hardcoded section names**

In `entries.py`, `_insert_entry_in_content` uses `r"\n## Bloccanti\n"`. Replace with:

```python
from mcp_cronos.config import load_config

def _insert_entry_in_content(content: str, entry: Entry) -> str:
    config = load_config()
    bloccanti_pattern = f"\n## {config.section_blockers}\n"
    bloccanti_match = re.search(re.escape(bloccanti_pattern), content)
    # ... rest same but use config.section_blockers and config.blockers_default
```

Same for `imposta_bloccanti`.

- [ ] **Step 2: Write tests/test_entries.py**

```python
"""Tests for entry management tools."""

import os
from datetime import date
from unittest.mock import patch

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.tools.entries import aggiungi_entry, imposta_bloccanti


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestAggiungiEntry:
    def test_creates_new_file(self, tmp_diario):
        with patch("mcp_cronos.tools.entries.get_today", return_value=date(2026, 4, 9)):
            result = aggiungi_entry(
                progetto="TestProj",
                descrizione="Test desc",
                paragrafo_intro="Did something.",
            )
        assert result["successo"] is True
        assert "2026-04-09.md" in result["file"]

    def test_appends_to_existing_file(self, sample_diary_it):
        with patch("mcp_cronos.tools.entries.get_today", return_value=date(2026, 4, 9)):
            result = aggiungi_entry(
                progetto="NewProj",
                descrizione="New work",
                paragrafo_intro="Started new project.",
                data="2026-04-09",
            )
        assert result["successo"] is True
        content = sample_diary_it.read_text()
        assert "NewProj" in content
        assert "TestProject" in content  # original still there

    def test_invalid_date(self, tmp_diario):
        result = aggiungi_entry(
            progetto="P", descrizione="D", paragrafo_intro="I",
            data="not-a-date",
        )
        assert "errore" in result

    def test_with_riferimenti(self, tmp_diario):
        with patch("mcp_cronos.tools.entries.get_today", return_value=date(2026, 4, 9)):
            result = aggiungi_entry(
                progetto="P", descrizione="D", paragrafo_intro="I",
                repository="my-repo", branch="feat/x",
                jira_ticket="PROJ-123", jira_url="https://jira.example.com/PROJ-123",
            )
        assert result["successo"] is True


class TestImpostaBloccanti:
    def test_updates_blockers(self, sample_diary_it):
        result = imposta_bloccanti(bloccanti="Blocked by deploy", data="2026-04-09")
        assert result["successo"] is True
        content = sample_diary_it.read_text()
        assert "Blocked by deploy" in content

    def test_file_not_found(self, tmp_diario):
        result = imposta_bloccanti(bloccanti="Blocked", data="2099-01-01")
        assert "errore" in result
```

- [ ] **Step 3: Migrate fine_giornata.py — use template loader**

Replace the hardcoded `STILE_FINE_GIORNATA` with:

```python
from mcp_cronos.template_loader import load_template
from mcp_cronos.config import load_config

def _get_style_instructions() -> str:
    config = load_config()
    template = load_template("fine_giornata")
    return template.format(
        section_entries=config.section_entries,
        section_blockers=config.section_blockers,
        section_day_summary=config.section_day_summary,
        section_tech_summary=config.section_tech_summary,
        section_standup_message=config.section_standup_message,
    )
```

Use `_get_style_instructions()` instead of `STILE_FINE_GIORNATA` in `fine_giornata()`.

Also replace hardcoded `"## Bloccanti"` string searches with config section name.

- [ ] **Step 4: Write tests/test_fine_giornata.py**

```python
"""Tests for end-of-day tool."""

import os
from datetime import date
from unittest.mock import patch

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.tools.fine_giornata import fine_giornata


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestFineGiornata:
    def test_returns_instructions(self, sample_diary_it):
        with patch("mcp_cronos.tools.fine_giornata.get_today", return_value=date(2026, 4, 9)):
            result = fine_giornata(data="2026-04-09")
        assert "istruzioni" in result
        assert result["data"] == "2026-04-09"
        assert len(result["istruzioni"]) > 100

    def test_file_not_found(self, tmp_diario):
        result = fine_giornata(data="2099-01-01")
        assert "errore" in result

    def test_returns_entries(self, sample_diary_it):
        result = fine_giornata(data="2026-04-09")
        assert "entries" in result or "contenuto_completo" in result
```

- [ ] **Step 5: Migrate standup.py — use template loader**

Replace `STILE_RIASSUNTO` with `load_template("standup")`. Replace hardcoded temporal strings with i18n temporal dict.

- [ ] **Step 6: Write tests/test_standup.py**

```python
"""Tests for standup tool."""

import os
from datetime import date
from unittest.mock import patch

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.tools.standup import genera_riassunto_standup


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestGeneraRiassuntoStandup:
    def test_returns_style_instructions(self, sample_diary_it):
        result = genera_riassunto_standup(data="2026-04-09")
        assert "istruzioni_stile" in result
        assert result["num_entries"] >= 1

    def test_no_entries_returns_error(self, tmp_diario):
        result = genera_riassunto_standup(data="2099-01-01")
        assert "errore" in result

    def test_returns_projects_list(self, sample_diary_it):
        result = genera_riassunto_standup(data="2026-04-09")
        assert "TestProject" in result["progetti"]
```

- [ ] **Step 7: Migrate consolida.py — use template loader**

Replace `STILE_CONSOLIDAMENTO` with `load_template("consolida")`. Replace hardcoded section names.

- [ ] **Step 8: Write tests/test_consolida.py**

```python
"""Tests for diary consolidation tool."""

import os
from datetime import date
from unittest.mock import patch

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.tools.consolida import consolida_diario


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestConsolidaDiario:
    def test_returns_instructions(self, sample_diary_it):
        result = consolida_diario(data="2026-04-09")
        assert "istruzioni" in result
        assert "contenuto_completo" in result

    def test_file_not_found(self, tmp_diario):
        result = consolida_diario(data="2099-01-01")
        assert "errore" in result

    def test_empty_file(self, tmp_diario):
        day_dir = tmp_diario / "2026" / "04"
        day_dir.mkdir(parents=True)
        f = day_dir / "2026-04-09.md"
        f.write_text("", encoding="utf-8")
        result = consolida_diario(data="2026-04-09")
        assert "errore" in result
```

- [ ] **Step 9: Migrate scrivi_fine_giornata.py — use config for git**

Update `_git_commit_and_push` to use config:

```python
from mcp_cronos.config import load_config

def _git_commit_and_push(file_path, file_date) -> dict:
    config = load_config()
    if not config.git_enabled:
        return {"git": "disabled"}
    # ... existing logic but use:
    commit_msg = config.commit_message.format(date=file_date)
    # ... skip push if not config.auto_push
```

- [ ] **Step 10: Write tests/test_scrivi.py**

```python
"""Tests for scrivi_fine_giornata."""

import os
from datetime import date
from unittest.mock import patch, MagicMock

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.tools.scrivi_fine_giornata import scrivi_fine_giornata


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestScriviFineGiornata:
    def test_writes_file(self, tmp_diario):
        config_file = tmp_diario / "cronos.toml"
        config_file.write_text('[cronos.git]\nenabled = false\n', encoding="utf-8")
        _reset_config()
        result = scrivi_fine_giornata(contenuto="# Test content", data="2026-04-09")
        assert result["successo"] is True
        written = (tmp_diario / "2026" / "04" / "2026-04-09.md").read_text()
        assert written == "# Test content"

    def test_git_disabled(self, tmp_diario):
        config_file = tmp_diario / "cronos.toml"
        config_file.write_text('[cronos.git]\nenabled = false\n', encoding="utf-8")
        _reset_config()
        result = scrivi_fine_giornata(contenuto="# Test", data="2026-04-09")
        assert result["git"]["git"] == "disabled"

    @patch("mcp_cronos.tools.scrivi_fine_giornata.subprocess.run")
    def test_git_commit_and_push(self, mock_run, tmp_diario):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = scrivi_fine_giornata(contenuto="# Test", data="2026-04-09")
        assert result["git"]["git_commit"] == "ok"
        assert result["git"]["git_push"] == "ok"

    @patch("mcp_cronos.tools.scrivi_fine_giornata.subprocess.run")
    def test_git_no_push_when_disabled(self, mock_run, tmp_diario):
        config_file = tmp_diario / "cronos.toml"
        config_file.write_text('[cronos.git]\nauto_push = false\n', encoding="utf-8")
        _reset_config()
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = scrivi_fine_giornata(contenuto="# Test", data="2026-04-09")
        assert result["git"]["git_push"] is None or result["git"].get("git_push") == "disabled"

    def test_invalid_date(self, tmp_diario):
        result = scrivi_fine_giornata(contenuto="# Test", data="bad")
        assert "errore" in result
```

- [ ] **Step 11: Migrate aggiungi_progetto.py — replace hardcoded section names**

Replace `r"\n## Bloccanti\n"` and similar with config section names.

- [ ] **Step 12: Write tests/test_aggiungi_progetto.py**

```python
"""Tests for aggiungi_a_progetto tool."""

import os
from datetime import date
from unittest.mock import patch

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.tools.aggiungi_progetto import aggiungi_a_progetto


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestAggiungiAProgetto:
    def test_creates_new_entry_if_no_file(self, tmp_diario):
        with patch("mcp_cronos.tools.aggiungi_progetto.get_today", return_value=date(2026, 4, 9)):
            result = aggiungi_a_progetto(
                progetto="NewProj", titolo_fase="Phase 1", contenuto="Did stuff.",
            )
        assert result["successo"] is True
        assert result["modalita"] == "nuova_entry"

    def test_appends_to_existing_project(self, sample_diary_it):
        result = aggiungi_a_progetto(
            progetto="TestProject", titolo_fase="Phase 2",
            contenuto="More work.", data="2026-04-09",
        )
        assert result["successo"] is True
        assert result["modalita"] == "aggiunto_a_esistente"
```

- [ ] **Step 13: Write tests/test_reader.py and tests/test_cerca.py and tests/test_settimana.py**

```python
# tests/test_reader.py
"""Tests for diary reader tools."""

import os
from datetime import date
from unittest.mock import patch

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.tools.reader import leggi_diario, lista_progetti


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestLeggiDiario:
    def test_reads_existing_file(self, sample_diary_it):
        result = leggi_diario(data="2026-04-09")
        assert result["riepilogo"]["files_trovati"] == 1

    def test_file_not_found(self, tmp_diario):
        result = leggi_diario(data="2099-01-01")
        assert result["riepilogo"]["files_mancanti"] == 1

    def test_invalid_date_range(self, tmp_diario):
        result = leggi_diario(data_inizio="2026-04-10", data_fine="2026-04-09")
        assert "errore" in result


class TestListaProgetti:
    def test_finds_projects(self, sample_diary_it):
        result = lista_progetti(data_inizio="2026-04-09", data_fine="2026-04-09")
        assert result["totale_progetti"] >= 1
```

```python
# tests/test_cerca.py
"""Tests for diary search tool."""

import os
from datetime import date
from unittest.mock import patch

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.tools.cerca import cerca_nel_diario


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestCercaNelDiario:
    def test_finds_match(self, sample_diary_it):
        result = cerca_nel_diario(
            query="TestProject",
            data_inizio="2026-04-09", data_fine="2026-04-09",
        )
        assert result["totale_risultati"] >= 1

    def test_no_match(self, sample_diary_it):
        result = cerca_nel_diario(
            query="NonExistentXYZ",
            data_inizio="2026-04-09", data_fine="2026-04-09",
        )
        assert result["totale_risultati"] == 0

    def test_invalid_regex(self, tmp_diario):
        result = cerca_nel_diario(query="[invalid")
        assert "errore" in result
```

```python
# tests/test_settimana.py
"""Tests for weekly summary tool."""

import os
from datetime import date
from unittest.mock import patch

import pytest

from mcp_cronos.config import _reset_config
from mcp_cronos.tools.settimana import riassunto_settimana


@pytest.fixture(autouse=True)
def reset(tmp_diario):
    _reset_config()
    yield
    _reset_config()


class TestRiassuntoSettimana:
    def test_returns_week_range(self, sample_diary_it):
        result = riassunto_settimana(data="2026-04-09")
        assert "settimana" in result
        assert "da" in result["settimana"]

    def test_empty_week(self, tmp_diario):
        result = riassunto_settimana(data="2099-01-06")
        assert result["giorni_lavorati"] == 0
```

- [ ] **Step 14: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 15: Commit**

```bash
git add src/mcp_cronos/tools/ tests/
git commit -m "refactor(tools): migrate all tools to config/i18n, add comprehensive tests"
```

---

### Task 9: Update pyproject.toml for PyPI

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update pyproject.toml**

```toml
[project]
name = "mcp-cronos"
version = "1.0.0"
description = "MCP server for structured daily work diary management with i18n support"
readme = "README.md"
requires-python = ">=3.10"
authors = [
    {name = "Maurizio Mocci", email = "mauriziomocci@gmail.com"}
]
keywords = ["mcp", "cronos", "diary", "standup", "markdown", "work-log"]
license = {text = "MIT"}
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Natural Language :: Italian",
    "Natural Language :: English",
    "Topic :: Office/Business",
]

dependencies = [
    "mcp>=1.0.0",
    "pydantic>=2.0.0",
    "tomli>=2.0.0; python_version < '3.11'",
]

[project.urls]
Homepage = "https://github.com/mauriziomocci/mcp-cronos"
Repository = "https://github.com/mauriziomocci/mcp-cronos"
Issues = "https://github.com/mauriziomocci/mcp-cronos/issues"
```

- [ ] **Step 2: Sync dependencies**

Run: `uv sync`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: update pyproject.toml for PyPI publishing"
```

---

### Task 10: Write bilingual README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Rewrite README.md**

Complete bilingual README with:
- English section: description, installation (`pip install mcp-cronos`), configuration (Claude Code settings.json + cronos.toml), all 11 tools documented, diary format, examples
- Italian section: same content translated
- Badges: PyPI version, license, Python versions

Cover: quick start, cronos.toml example, custom templates, git integration, all tools with parameters.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(readme): bilingual README with full tool documentation"
```

---

### Task 11: Add GitHub Action for PyPI publish

**Files:**
- Create: `.github/workflows/publish.yml`

- [ ] **Step 1: Create publish workflow**

Copy the pattern from deep-reasoning-mcp (tag-triggered PyPI publish):

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - "v*"

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

- [ ] **Step 2: Commit**

```bash
git add .github/
git commit -m "chore: add GitHub Action for PyPI publishing on tag"
```

---

### Task 12: Update CLAUDE.md and final verification

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md**

Add sections for:
- New modules (`i18n.py`, `config.py` expanded, `template_loader.py`, `default_templates/`)
- Configuration conventions (cronos.toml, env vars)
- How to add a new language
- Updated architecture diagram

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Run linter and formatter**

Run: `uv run ruff check src/mcp_cronos/ && uv run ruff format --check src/mcp_cronos/`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): update CLAUDE.md with i18n and config conventions"
```

- [ ] **Step 5: Push all commits**

```bash
git push
```
