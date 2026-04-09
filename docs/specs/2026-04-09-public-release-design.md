# mcp-cronos Public Release Design Spec

**Date**: 2026-04-09
**Status**: Approved
**Goal**: Make mcp-cronos a publishable PyPI package with full i18n, configurable templates, test suite, and updated documentation.

---

## 1. Configuration System

### 1.1 Config file location (searched in order)

1. `{CRONOS_DIARIO_PATH}/cronos.toml`
2. `~/.config/cronos/cronos.toml`
3. No file found: use built-in defaults (Italian)

### 1.2 Config schema

```toml
[cronos]
lang = "it"  # Language code. Built-in: "it", "en". Default: "it"

[cronos.diary]
title_format = "Per lo Stand-up {date}"
date_format = "{day} {month} {year}"

[cronos.sections]
entries = "Cosa ho fatto ieri"
blockers = "Bloccanti"
blockers_default = "Nessuno"
day_summary = "Riassunto della giornata"
tech_summary = "Riassunto tecnico"
standup_message = "Messaggio per lo standup"

[cronos.git]
enabled = true
commit_message = "diario: fine giornata {date}"
auto_push = true
```

All keys are optional. Missing keys fall back to the language default, then to Italian.

### 1.3 Environment variables

- `CRONOS_DIARIO_PATH` (mandatory): path to diary root directory
- `CRONOS_CONFIG_PATH` (optional): explicit path to config file, overrides search order

### 1.4 Config loading logic

```
load_config():
    path = CRONOS_CONFIG_PATH env var
         or {CRONOS_DIARIO_PATH}/cronos.toml
         or ~/.config/cronos/cronos.toml
         or None

    if path exists:
        user_config = parse TOML
    else:
        user_config = {}

    lang = user_config.get("cronos.lang", "it")
    lang_defaults = LANGUAGES[lang]  # from i18n module

    return merge(lang_defaults, user_config)
```

Priority: user config > language defaults > Italian defaults.

---

## 2. Internationalization (i18n)

### 2.1 Language registry

Module `i18n.py` with a `LANGUAGES` dict. Each language provides:

```python
@dataclass
class LanguagePack:
    months: list[str]          # 12 month names
    weekdays: list[str]        # 7 weekday names (Monday first)
    title_prefix: str          # e.g. "Per lo Stand-up"
    date_format: str           # e.g. "{day} {month} {year}"
    sections: dict[str, str]   # entries, blockers, day_summary, tech_summary, standup_message
    blockers_default: str      # e.g. "Nessuno"
    temporal: dict[str, str]   # yesterday, day_before, last_weekday pattern
```

### 2.2 Built-in languages

- **Italian** (`it`): current hardcoded values (default)
- **English** (`en`): translated equivalents

### 2.3 Config overrides

Individual values from `cronos.toml` override language pack values. This allows partial customization (e.g., Italian language but custom section names).

---

## 3. Template System

### 3.1 LLM style templates

Three templates currently hardcoded as Python strings:
- `STILE_FINE_GIORNATA` in `fine_giornata.py`
- `STILE_RIASSUNTO` in `standup.py`
- `STILE_CONSOLIDAMENTO` in `consolida.py`

### 3.2 Externalization

Built-in defaults moved to `src/mcp_cronos/default_templates/`:
- `fine_giornata.md`
- `standup.md`
- `consolida.md`

User overrides searched in:
1. `{CRONOS_DIARIO_PATH}/templates/` (next to the diary)
2. Config file directory `/templates/` (next to cronos.toml)

If not found, use built-in defaults.

### 3.3 Template variables

Templates can use `{section_entries}`, `{section_blockers}`, `{section_day_summary}`, `{section_tech_summary}`, `{section_standup_message}` placeholders that get replaced with the configured section names. This ensures templates work regardless of language.

---

## 4. Module Changes

### 4.1 New modules

| Module | Purpose |
|--------|---------|
| `i18n.py` | Language packs, `get_lang()` helper |
| `default_templates/fine_giornata.md` | Built-in end-of-day template |
| `default_templates/standup.md` | Built-in standup template |
| `default_templates/consolida.md` | Built-in consolidation template |

### 4.2 Modified modules

| Module | Changes |
|--------|---------|
| `config.py` | Load and merge cronos.toml, expose `get_config()` singleton |
| `utils/dates.py` | Use i18n for months/weekdays instead of hardcoded `MESI_ITALIANI` |
| `utils/markdown.py` | Use config section names for parsing instead of hardcoded strings |
| `templates.py` | Use config section names for markdown generation |
| `tools/entries.py` | Use config section names |
| `tools/fine_giornata.py` | Load template from file or built-in, replace section placeholders |
| `tools/standup.py` | Load template from file or built-in |
| `tools/consolida.py` | Load template from file or built-in |
| `tools/scrivi_fine_giornata.py` | Use config for git commit message and auto_push flag |
| `tools/reader.py` | No changes expected |
| `tools/cerca.py` | No changes expected |
| `tools/settimana.py` | No changes expected |
| `tools/aggiungi_progetto.py` | Use config section names for regex patterns |

### 4.3 Config access pattern

All modules call `config.get_config()` which returns a cached `CronosConfig` dataclass. The config is loaded once at first access and cached for the process lifetime.

---

## 5. Git Integration

### 5.1 Current behavior

`scrivi_fine_giornata` runs git add + commit + push unconditionally.

### 5.2 New behavior

Controlled by `[cronos.git]` config:
- `enabled = true`: run git operations (default: true)
- `commit_message = "diario: fine giornata {date}"`: customizable, `{date}` replaced
- `auto_push = true`: push after commit (default: true)

If `enabled = false`, skip all git operations.

---

## 6. Test Suite

### 6.1 Structure

```
tests/
  conftest.py              # shared fixtures (tmp diary, mock config)
  test_config.py           # config loading, merge, fallback
  test_i18n.py             # language packs, get_lang()
  test_entries.py          # aggiungi_entry, imposta_bloccanti
  test_reader.py           # leggi_diario, lista_progetti
  test_standup.py          # genera_riassunto_standup
  test_fine_giornata.py    # fine_giornata
  test_scrivi.py           # scrivi_fine_giornata + git mock
  test_consolida.py        # consolida_diario
  test_cerca.py            # cerca_nel_diario
  test_settimana.py        # riassunto_settimana
  test_aggiungi_progetto.py # aggiungi_a_progetto
  test_dates.py            # date utilities
  test_markdown.py         # markdown parsing/rendering
  test_templates.py        # template loading, placeholder replacement
```

### 6.2 Fixtures

- `tmp_diario`: temporary diary directory with sample files
- `mock_config`: CronosConfig with test values
- `sample_diary_it`: sample Italian diary content
- `sample_diary_en`: sample English diary content

### 6.3 Coverage targets

- Every tool function: happy path + error cases
- Config: missing file, partial config, invalid TOML, env var override
- i18n: both languages, unknown language fallback
- Git: success, nothing to commit, push failure, git disabled
- Parsing: Italian sections, English sections, mixed/malformed content
- Edge cases: empty files, missing sections, no entries

---

## 7. PyPI and Documentation

### 7.1 pyproject.toml updates

- Description in English
- Classifiers: Development Status 4 Beta, Framework MCP, Natural Language Italian/English
- Project URLs: Homepage, Repository, Issues
- Add `tomli` dependency (TOML parsing for Python <3.11, stdlib `tomllib` for 3.11+)

### 7.2 README

Bilingual structure:
- English section first (for PyPI audience)
- Italian section below
- Both cover: installation, configuration, tools, diary format, examples

### 7.3 GitHub Action

Publish to PyPI on tag push (same pattern as deep-reasoning-mcp).

---

## 8. Scope Exclusions

- No web UI or dashboard
- No multi-user support
- No database backend (files only)
- No streaming or async I/O changes
- No new tools (only modify existing ones)
- No migration tool for existing diaries (users manually add cronos.toml if they want non-Italian)
