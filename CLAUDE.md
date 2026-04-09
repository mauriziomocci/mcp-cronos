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

**Stack**: Python 3.10+ | MCP SDK (mcp.server) | Pydantic 2.x | dataclasses | pathlib

**Package**: `src/mcp_cronos/`

```
src/mcp_cronos/
  __init__.py           # Package entry point, version
  server.py             # MCP server, tool definitions and dispatch (11 tools)
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
  utils/
    dates.py            # Date parsing, file path calculation, standup title (i18n-aware)
    markdown.py         # Diary file parsing, entry extraction, markdown rendering
```

**Design pattern**: the server is synchronous (no async tool logic). Tools read/write markdown files directly via pathlib. Tools that require LLM reasoning (fine_giornata, consolida, standup) return raw data + style instructions — the LLM generates the output.

**Configuration system**:
- `CRONOS_DIARIO_PATH` (env var, mandatory): path to diary root directory
- `CRONOS_CONFIG_PATH` (env var, optional): explicit path to config file
- `cronos.toml` (searched in diary root or `~/.config/cronos/`): language, section names, git settings, template overrides
- Priority: user config > language defaults > Italian defaults

**i18n**: built-in Italian (default) and English. Section names, month/weekday names, temporal strings, and blockers default are all language-aware. LLM templates use `{section_*}` placeholders resolved at runtime.

**Tool workflow**:
- Daily entries: `cronos_aggiungi_entry` / `cronos_aggiungi_a_progetto` (append to existing)
- Reading: `cronos_leggi_diario` / `cronos_cerca` / `cronos_lista_progetti` / `cronos_settimana`
- End of day: `cronos_fine_giornata` -> LLM generates content -> `cronos_scrivi_fine_giornata` (+ git commit/push)
- Consolidation: `cronos_consolida_diario` -> LLM rewrites -> file write
- Standup: `cronos_riassunto_standup` -> LLM generates message

**Diary file structure**: `{CRONOS_DIARIO_PATH}/{year}/{month}/{year}-{month}-{day}.md`

## Agent Rules

### CRITICAL: Understand Before Implementing

Before writing any code, invest time in understanding the full context: how the existing system works, why it works that way, and what already exists. Read the affected files thoroughly. Never assume — verify in source code.

### CRITICAL: Verify Before Asserting

Never present assumptions or hypotheses as verified facts. If something has not been verified in source code, say so explicitly.

### Core Behavior

- **Read CLAUDE.md first** before starting any task
- **Read and understand existing files** before modifying code
- Avoid over-engineering: only implement what is requested
- Prefer editing existing files over creating new ones
- All code, comments, docstrings, and documentation in **English**
- PEP 8 with 100 character line limit (as per ruff config), double quotes
- Tests: **zero failing tests**

### Execution Discipline

1. **Plan before acting**: understand the codebase context, then act
2. **Understand before implementing**: never start coding before understanding the existing system
3. **Verify before asserting**: never state something as fact without checking source code
4. **Handle errors, do not ignore them**: read error messages carefully, diagnose root cause, fix and re-test
5. **Ask for clarification when needed**: if requirements are ambiguous, ask before proceeding

### Code Comments and Docstrings

- **Language**: English, professional and precise
- **No emoji** in any context
- **Docstring content**: explain the "why" beyond the "what". Document non-obvious technical decisions

### Documentation Sync

After any code change, update all affected documentation **in the same commit**:
- **Docstrings**: update if method signature, behavior, or return value changed
- **README.md**: update if the change affects tools, configuration, or usage

### Mandatory Code Review

After writing any code, **before proposing a commit**, perform a thorough review:

1. **Pythonic style**: clean, idiomatic Python
2. **DRY violations**: duplicated logic that can be extracted
3. **Exception handling**: specific exceptions, no bare `except Exception` if the expected type is known
4. **Codebase consistency**: naming, patterns, type annotations
5. **Security**: no sensitive data in logs, no command injection, no unvalidated external input
6. **Documentation**: docstrings updated, README updated if needed

Fix issues before committing. Report what was found and corrected.

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
Scope: module name (e.g. `server`, `entries`, `reader`, `standup`, `fine_giornata`, `consolida`, `cerca`, `settimana`, `dates`, `markdown`, `templates`, `config`)

**FORBIDDEN**: References to Claude/AI, emoji, Co-Authored-By, attribution lines.

## Conventions

### Adding a New Tool

1. Create tool function in `tools/` (new file or existing, depending on domain)
2. Add `Tool(...)` definition in `server.py` `TOOLS` list with full description and inputSchema
3. Add handler case in `call_tool()` dispatch in `server.py`
4. Import the function in `server.py`
5. Update `__init__.py` docstring
6. Update `README.md` tool section
7. Add tests

### Modifying an Existing Tool

1. Update the function in `tools/`
2. If parameters changed, update `inputSchema` in `server.py`
3. If description changed, update `Tool.description` in `server.py`
4. Update tests

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

## Known Limitations

- **Synchronous I/O**: all file operations are synchronous (pathlib read/write). Acceptable for single-user local diary.
- **No file locking**: concurrent writes to the same diary file could conflict. Not an issue for single-user use.
- **Tool dispatch is manual**: `call_tool()` uses if/elif chains instead of a registry. Acceptable for 11 tools.
