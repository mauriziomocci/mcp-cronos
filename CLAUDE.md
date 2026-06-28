# CLAUDE.md

Guide for Claude Code - mcp-cronos: MCP server for daily work diary management.

## Quick Reference

```bash
# Install dependencies
uv sync

# Run the server locally
uv run mcp-cronos

# Run tests
uv run pytest

# Format
uv run ruff format src/mcp_cronos/

# Lint
uv run ruff check src/mcp_cronos/
```

## Architecture

**Stack**: Python 3.10+ | MCP SDK (mcp.server) | Pydantic 2.x | dataclasses | pathlib | holidays

**Package**: `src/mcp_cronos/`

```
src/mcp_cronos/
  __init__.py           # Package entry point, version
  server.py             # MCP server, tool definitions and dispatch (19 tools)
  config.py             # Configuration: TOML loading, CronosConfig singleton
  i18n.py               # Language packs (Italian, English), LanguagePack dataclass
  template_loader.py    # LLM template loading with user override support
  templates.py          # Dataclasses (Entry, Riferimento, DiarioGiornaliero), markdown generation
  default_templates/    # Built-in LLM prompt templates
    fine_giornata.md    # End-of-day style instructions
    standup.md          # Standup message style instructions
    consolida.md        # Consolidation style instructions
  tools/
    entries.py          # cronos_aggiungi_entry, cronos_imposta_bloccanti
    reader.py           # cronos_leggi_diario, cronos_lista_progetti
    standup.py          # cronos_riassunto_standup
    fine_giornata.py    # cronos_fine_giornata (end-of-day with LLM instructions)
    scrivi_fine_giornata.py  # cronos_scrivi_fine_giornata (write + git commit/push)
    consolida.py        # cronos_consolida_diario
    cerca.py            # cronos_cerca (full-text search with regex)
    settimana.py        # cronos_settimana (weekly summary by project)
    aggiungi_progetto.py  # cronos_aggiungi_a_progetto (append to existing entry)
    leggi_todo.py         # cronos_leggi_todo (read todo.md for a date)
    lista_mese.py         # cronos_lista_mese (month dashboard of diary artifacts)
    prepara_domani.py     # cronos_prepara_domani (set up next working day folder)
    audit_progetti.py     # cronos_audit_progetti (scan headings, cluster names, generate bozza_toml)
    dossier.py            # cronos_progetto (full project/system story: timeline, refs, per-component counts, blockers)
    statistiche.py        # cronos_statistiche (work distribution by project/system: entry counts, days, quota_pct, per-month trend)
    riferimento.py        # cronos_riferimento (cross-reference search: timeline of every diary entry mentioning a ticket/MR/repo, with projects and systems)
    igiene.py             # cronos_igiene (read-only hygiene advisor: unmapped headings, unclosed fences, missing working days, unclosed days)
  utils/
    dates.py            # Date parsing, file path calculation, standup title (i18n-aware)
    markdown.py         # Diary file parsing, entry extraction, markdown rendering
    projects.py         # Project registry: load [cronos.projects], canonical resolution, system_of()
```

**Design pattern**: the server is synchronous (no async tool logic). Tools read/write markdown files directly via pathlib. Tools that require LLM reasoning (fine_giornata, consolida, standup) return raw data + style instructions — the LLM generates the output.

**Configuration system**:
- `CRONOS_DIARIO_PATH` (env var, mandatory): path to diary root directory
- `CRONOS_CONFIG_PATH` (env var, optional): explicit path to config file
- `cronos.toml` (searched in diary root or `~/.config/cronos/`): language, section names, git settings, template overrides
- `[cronos.calendar]`: `country` (ISO code, default `"IT"`) and `extra_holidays` (list of `YYYY-MM-DD` strings). Working-day calculation in `cronos_prepara_domani` and standup last-working-day logic is holiday-aware: skips national holidays for the configured country plus `extra_holidays`, in addition to weekends.
- Priority: user config > language defaults > Italian defaults
- An optional, domain-agnostic `[cronos.projects]` registry enables canonical project identity and a two-level system → component view; it is opt-in and empty by default.

**i18n**: built-in Italian (default) and English. Section names, month/weekday names, temporal strings, and blockers default are all language-aware. LLM templates use `{section_*}` placeholders resolved at runtime.

**Tool workflow**:
- Daily entries: `cronos_aggiungi_entry` / `cronos_aggiungi_a_progetto` (append to existing). Both tools auto-detect `repository` and `branch` from git when those parameters are omitted; pass `working_dir` to control which directory is inspected.
- Reading: `cronos_leggi_diario` / `cronos_cerca` / `cronos_lista_progetti` / `cronos_settimana` / `cronos_leggi_todo` / `cronos_lista_mese`
- End of day: `cronos_fine_giornata` -> LLM generates content -> `cronos_scrivi_fine_giornata` (+ git commit/push). Pass `contenuto_todo` to `cronos_scrivi_fine_giornata` to prepare the next working day's folder in a single call, avoiding a separate `cronos_prepara_domani` invocation.
- Consolidation: `cronos_consolida_diario` -> LLM rewrites -> file write
- Standup: `cronos_riassunto_standup` -> LLM generates message
- Project/system story: `cronos_progetto` returns the full per-project or per-system dossier (chronological timeline, aggregated references, per-component counts, blockers) — read-only, capped output
- Work distribution: `cronos_statistiche` gives work distribution by project and system over a period (entry counts, distinct days, per-system quota_pct, per-month activity trend) — read-only, capped output
- Cross-reference search: `cronos_riferimento` traces a reference (ticket/MR/repo) across the diary — every entry mentioning it, chronologically, with the projects and systems it spans — read-only, capped output
- Diary hygiene: `cronos_igiene` scans the diary read-only and reports unmapped headings, unclosed fences, missing working days, and unclosed days — with severity and actionable suggestions

**Diary file structure**: current per-day folder layout
`{CRONOS_DIARIO_PATH}/{year}/{month}/{year}-{month}-{day}/` containing `raw.md`
(progressive daily log), `fine-giornata.md` (end-of-day closure), and `todo.md`
(day's to-do list). Legacy days use a single file
`{CRONOS_DIARIO_PATH}/{year}/{month}/{year}-{month}-{day}.md` and are kept as-is
(no migration).

## Agent Rules

Le regole-agente generali si applicano dal CLAUDE.md globale (`~/.claude/CLAUDE.md`) e NON sono ricopiate qui: understand-before-implementing, verify-before-asserting, reuse-before-reinventing, no-bug-left-behind, evidence-based-verification, Core Behavior, Execution Discipline, Documentation Sync. La Mandatory Code Review segue la checklist a 8 punti del globale; per questo MCP non-Django i controlli specifici di Django (N+1/ORM, permessi sulle viste) si applicano solo dove pertinenti.

Override e parametri locali di questo progetto:
- **Lingua**: tutto il codice, commenti, docstring e documentazione in **inglese** (override del default italiano globale).
- **Stile**: PEP 8, limite 100 caratteri (config ruff), virgolette doppie.
- **No emoji** in nessun contesto.

## Mandatory Rules

### Security

- NEVER log API keys, tokens, or credentials
- NEVER include hardcoded secrets in source code
- Validate all tool input parameters
- File operations are restricted to paths under `CRONOS_DIARIO_PATH`

### Test Quality

- Zero failing tests
- Test each tool function independently
- Test edge cases: missing files, invalid dates, empty diary, malformed markdown
- Test both "file exists" and "file does not exist" paths

### Git Commits

```
type(scope): brief description

CHANGE: Technical explanation.
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
Scope: module name (e.g. `server`, `entries`, `reader`, `standup`, `fine_giornata`, `consolida`, `cerca`, `settimana`, `dates`, `markdown`, `templates`, `config`, `leggi_todo`, `lista_mese`, `prepara_domani`, `i18n`, `template_loader`, `workdays`, `gitinfo`, `projects`, `audit_progetti`, `dossier`, `statistiche`, `riferimento`, `igiene`)

**FORBIDDEN**: References to Claude/AI, emoji, Co-Authored-By, attribution lines.

## Conventions

> **Documentation is a hard rule (regola ferrea).** Every change to the MCP updates the docs in the SAME cycle, in BOTH language parts of `README.md`: the per-tool `####` reference AND the usage manual (`### Usage guide` / `### Guida all'uso`) how-to recipe, plus `CLAUDE.md` (tool count, tree) and a `CHANGELOG.md` `[Unreleased]` entry. A new tool must appear both in the reference and in its workflow group of the manual; a changed parameter must be reflected in both. Manual examples use real parameter names (checked against the schema) and neutral placeholders only (no domain names).

### Adding a New Tool

1. Create tool function in `tools/` (new file or existing, depending on domain)
2. Add `Tool(...)` definition in `server.py` `TOOLS` list with full description and inputSchema
3. Add handler case in `call_tool()` dispatch in `server.py`
4. Import the function in `server.py`
5. Update `__init__.py` docstring
6. Add tests
7. Docs in the same cycle (mandatory): the tool's `####` reference in `README.md` (EN + IT); a how-to recipe in the README usage guide (`### Usage guide` / `### Guida all'uso`), in the right workflow group, both languages; bump the tool count in `CLAUDE.md`; add a `[Unreleased]` entry in `CHANGELOG.md`

### Modifying an Existing Tool

1. Update the function in `tools/`
2. If parameters changed, update `inputSchema` in `server.py`
3. If description changed, update `Tool.description` in `server.py`
4. Update tests
5. Docs in the same cycle if behaviour/parameters/return changed: the tool's `####` reference (EN + IT), its how-to recipe in the README usage guide (EN + IT), and a `[Unreleased]` entry in `CHANGELOG.md`

### Diary File Format

Section names are configurable via `cronos.toml` and i18n. Default (Italian):

```markdown
# Per lo Stand-up {Day+1} {Month} {Year}

## Cosa ho fatto ieri

### {Project} - {Description}

{Intro paragraph}

{Content}

**Riferimenti:**
- Repository: name
- Branch: `branch`
- Jira: [TICKET](url)
- GitLab MR: [MR !123](url)

---

## Bloccanti

Nessuno
```

The title uses the next day's date (standup convention). Months and section names follow the configured language. Entries are separated by `---`. The blockers section is always at the end.

### Adding a New Language

1. Add a `LanguagePack` entry in `i18n.py` `LANGUAGES` dict
2. Provide: months, weekdays, title_prefix, date_format, sections, blockers_default, temporal
3. Add tests in `tests/test_i18n.py`
4. Update README.md

### End-of-Day Workflow

The end-of-day process is a two-step tool workflow:

1. `cronos_fine_giornata` reads raw entries and returns them with detailed style instructions
2. The LLM generates the restructured content (5 sections: entries, daily summary, technical summary, standup message, blockers)
3. `cronos_scrivi_fine_giornata` writes the generated content to the file

After writing the end-of-day file, commit and push the diary changes.

4. Optionally call `cronos_prepara_domani` to create the next working day's
   folder with a `todo.md` and an empty `raw.md` skeleton, carrying over open
   points from the day just closed.

## Known Limitations

- **Synchronous I/O**: all file operations are synchronous (pathlib read/write). Acceptable for single-user local diary.
- **No file locking**: concurrent writes to the same diary file could conflict. Not an issue for single-user use.
- **Tool dispatch is manual**: `call_tool()` uses if/elif chains instead of a registry. Acceptable for 19 tools.
