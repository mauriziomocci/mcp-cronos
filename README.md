# mcp-cronos

[![PyPI](https://img.shields.io/pypi/v/mcp-cronos)](https://pypi.org/project/mcp-cronos/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

MCP server for structured daily work diary management — entries, standup summaries, weekly reports, full-text search, and automatic git commits.

---

## English

### Features

- **Add entries**: Add new work entries to the daily diary, creating files and directories automatically
- **Read diary**: Read entries by single date, date range, or last N days
- **Standup summary**: Generate a high-level, narrative summary ready for standup meetings
- **Blockers management**: Set and update the blockers section of any diary file
- **End-of-day workflow**: Rewrite and restructure the day's entries, generate day summary, technical summary, and standup message
- **Consolidate diary**: Merge fragmented or duplicate entries into a coherent file
- **List projects**: List all projects worked on in a given period
- **Full-text search**: Search diary entries with regex support
- **Weekly report**: Summarize the week grouped by project
- **Append to project**: Add a sub-section to an existing project entry without fragmentation
- **Write end-of-day file**: Persist the structured end-of-day content to disk
- **Read todo**: Read the `todo.md` for a given day (what was planned)
- **Month dashboard**: At-a-glance month view of which artifacts exist per day
- **Prepare next day**: Create the next working day's folder with todo and raw skeleton
- **Internationalisation**: Built-in Italian and English language packs, configurable via `cronos.toml`
- **Git commits**: Automatic commit (and optional push) of the diary at end-of-day
- **Reference metadata**: Repository, branch, Jira ticket and GitLab MR are recorded on entries as plain-text references — used for search and roll-up. Cronos does **not** call the Jira or GitLab APIs; there is no live integration.

### Installation

```bash
pip install mcp-cronos
```

Or with `uv`:

```bash
uv add mcp-cronos
```

### Configuration

#### Claude Code (`settings.json`)

Add the following to your Claude Code settings file (typically `~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "cronos": {
      "command": "uvx",
      "args": ["mcp-cronos"],
      "env": {
        "CRONOS_DIARIO_PATH": "/path/to/your/Diary"
      }
    }
  }
}
```

If you are running from a local checkout instead of the published package:

```json
{
  "mcpServers": {
    "cronos": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/Cronos",
        "run",
        "mcp-cronos"
      ],
      "env": {
        "CRONOS_DIARIO_PATH": "/path/to/your/Diary"
      }
    }
  }
}
```

The `CRONOS_DIARIO_PATH` environment variable is required. It must point to the root directory of your diary.

#### `cronos.toml`

Place a `cronos.toml` file in your diary root directory (i.e. `$CRONOS_DIARIO_PATH/cronos.toml`), or at `~/.config/cronos/cronos.toml`. An explicit path can also be set via the `CRONOS_CONFIG_PATH` environment variable.

All settings are optional and fall back to language-specific defaults when omitted.

```toml
[cronos]
# Language: "it" (default) or "en"
lang = "en"

[cronos.sections]
# Override section heading labels used in diary files.
# These must match the headings already present in existing files if you
# are migrating from the default Italian labels.
entries        = "What I did yesterday"
blockers       = "Blockers"
day_summary    = "Daily summary"
tech_summary   = "Technical summary"
standup_message = "Standup message"

[cronos.diary]
# Format string for the file title. Supports {date} placeholder.
title_format = "For Stand-up - {date}"

[cronos.git]
# Enable automatic git commit at end-of-day (default: true)
enabled = true
# Push after committing (default: true)
auto_push = true
# Commit message template. Supports {date} placeholder.
commit_message = "diary: end of day {date}"

[cronos.calendar]
# ISO country code for the national holiday calendar (default "IT").
country = "IT"
# Extra dates treated as holidays (bridges, company closures), YYYY-MM-DD.
extra_holidays = ["2026-12-07"]
```

The next/previous working-day calculation used by `cronos_prepara_domani` and by the standup summary skips the configured country's national holidays plus `extra_holidays`, in addition to weekends.

#### Project registry (optional)

The project registry is entirely optional. Cronos works out-of-the-box with no project configuration at all, and no project names are hardcoded in the package.

When you want a two-level system → component view and canonical project identity across name variants, add a `[cronos.projects]` section to your `cronos.toml`:

```toml
[cronos.projects.api-gateway]
sistema = "Platform"
alias = ["APIGateway", "api gw"]

[cronos.projects.billing]
sistema = "Platform"
```

Each `[cronos.projects.<name>]` declares an optional parent `sistema` (the group or product area the component belongs to) and optional `alias` synonyms. Case, spacing, and punctuation variants are matched automatically, so `alias` is only needed for genuinely different names — not for `"API Gateway"` vs `"api gateway"`.

The easiest way to build this list is to run `cronos_audit_progetti`, which scans your diary headings and returns a ready-made `bozza_toml` draft clustered by normalized name. Copy that draft into your `cronos.toml`, add `sistema` where you want hierarchy, and you are done.

#### Custom Templates

Template files for generated output (end-of-day file, standup message, etc.) can be placed in a `templates/` subdirectory inside your diary root. When present, these override the built-in defaults. The server loads templates from `$CRONOS_DIARIO_PATH/templates/` automatically.

### Getting started

The simplest way to go from a fresh diary to a fully working project registry is a two-step loop: `cronos_audit_progetti` builds the list, `cronos_igiene` maintains it.

1. **Write your diary entries as usual**, using `### ProjectName - Short description` headings.
2. **Run `cronos_audit_progetti`**: it scans the diary headings, clusters spelling variants, and produces a ready-to-paste `[cronos.projects]` draft (`bozza_toml`).
3. **Paste the draft into `cronos.toml`** (under `$CRONOS_DIARIO_PATH/cronos.toml`). Add a `sistema` field where you want hierarchy, tweak aliases if needed — the tool does the grouping work for you.
4. **Run `cronos_igiene`**: it verifies that every heading now resolves to a registered project, flags working days with no diary, unclosed code fences, and days that were never closed. Act on its suggestions to keep the diary clean.

Repeat step 4 whenever you add new projects or notice gaps. Re-run step 2 whenever the diary has grown and new project names have appeared that are not yet in the registry.

### Usage guide

This section is a practical how-to guide grouped by goal. Each recipe tells you which tool to call and with which key arguments; it does not repeat every parameter — see the [Tools](#tools) reference below for the full signatures. Start here when you want to accomplish something; go to the reference when you need exact parameter names or return-value details.

#### During the day

Use these tools to capture work as it happens, add context to existing entries, note blockers, and check what was planned.

**Log a piece of work.** To record what you did on a project, call [`cronos_aggiungi_entry`](#cronos_aggiungi_entry):

```python
Tool(name="cronos_aggiungi_entry", arguments={
    "progetto": "Alpha",
    "descrizione": "fix login redirect",
    "jira_ticket": "ABC-123"
})
```

This creates today's diary file (and the year/month folder) if they do not exist yet, and appends a `### Alpha - fix login redirect` entry. Omit `jira_ticket` when there is no ticket; supply `repository` and `branch` explicitly or let the tool detect them from git.

**Add a second session to the same project without fragmenting.** If you worked on `Alpha` again later in the day, append a sub-section instead of creating a duplicate heading, using [`cronos_aggiungi_a_progetto`](#cronos_aggiungi_a_progetto):

```python
Tool(name="cronos_aggiungi_a_progetto", arguments={
    "progetto": "Alpha",
    "titolo_fase": "code review pass",
    "contenuto": "Reviewed PR !42 — left two comments on error handling."
})
```

The tool finds the existing `### Alpha` heading and appends an `#### code review pass` block underneath it. If no matching heading exists, it falls back to creating a new standard entry.

**Record a blocker.** Once the diary file exists for today, set the Blockers section with [`cronos_imposta_bloccanti`](#cronos_imposta_bloccanti):

```python
Tool(name="cronos_imposta_bloccanti", arguments={
    "bloccanti": "Waiting for Beta team sign-off on the API contract."
})
```

Call it again later to overwrite with `"None"` once the blocker is resolved.

**Check what was planned.** To read the to-do list for today (or any day), call [`cronos_leggi_todo`](#cronos_leggi_todo):

```python
Tool(name="cronos_leggi_todo", arguments={})
```

If a previous [`cronos_prepara_domani`](#cronos_prepara_domani) run backed up an older plan, its path is reported alongside the current content.

#### Closing the day

The end-of-day is a deliberate two-phase flow. `cronos_fine_giornata` reads the raw entries and returns generation instructions; the AI assistant then drafts the structured content; finally `cronos_scrivi_fine_giornata` persists it to disk. Keep the two calls separate — do not merge them into one step.

**Phase 1 — trigger the end-of-day workflow.** Call [`cronos_fine_giornata`](#cronos_fine_giornata) to get the raw diary and the instructions for generating the four structured outputs (rewritten entries, day summary, technical summary, standup message):

```python
Tool(name="cronos_fine_giornata", arguments={})
```

Follow the returned instructions to draft the content. You are editing the narrative here, not writing to disk yet.

**Phase 2 — persist the generated file.** Once the content is ready, call [`cronos_scrivi_fine_giornata`](#cronos_scrivi_fine_giornata) to write `fine-giornata.md`. Optionally pass a todo draft for the next day in the same call to skip a separate [`cronos_prepara_domani`](#cronos_prepara_domani) step:

```python
Tool(name="cronos_scrivi_fine_giornata", arguments={
    "contenuto": "... full markdown content ...",
    "contenuto_todo": "## Tomorrow\n- Review Beta API spec\n- ABC-124 implementation"
})
```

When `contenuto_todo` is provided, the next working day's `todo.md` and `raw.md` skeleton are created automatically.

**Prepare the next day separately.** If you prefer to plan tomorrow as a dedicated step (for example, after a standup where priorities shifted), call [`cronos_prepara_domani`](#cronos_prepara_domani) on its own:

```python
Tool(name="cronos_prepara_domani", arguments={
    "contenuto_todo": "## 2026-07-01\n- ABC-124 implementation\n- Deploy to staging"
})
```

The tool targets the next working day automatically, skipping weekends and public holidays. Supply an explicit `data` to plan a specific future date instead.

**Generate a standup message.** To produce a polished, narrative standup from yesterday's diary (or any date range), call [`cronos_riassunto_standup`](#cronos_riassunto_standup):

```python
Tool(name="cronos_riassunto_standup", arguments={})
```

The tool returns the raw diary content together with style instructions so the AI assistant can draft a fluent message free of implementation details. Supply `data_inizio` and `data_fine` to cover a multi-day span (for example, after a long weekend).

#### Reading the diary back

Use these tools to retrieve what was written, whether you need a single day, a week, a month, or a targeted search.

**Read one day or a range.** Call [`cronos_leggi_diario`](#cronos_leggi_diario) with no arguments to get today's diary, a single date, a date range, or the last N days:

```python
# Today
Tool(name="cronos_leggi_diario", arguments={})

# A specific day
Tool(name="cronos_leggi_diario", arguments={"data": "2026-06-20"})

# Last 5 days
Tool(name="cronos_leggi_diario", arguments={"ultimi_giorni": 5})
```

The `riepilogo` field in the response reports which dates had no file, so you can spot gaps at a glance.

**Get a weekly overview.** To see the current week grouped by project (how many days each project was active and what was done), call [`cronos_settimana`](#cronos_settimana):

```python
Tool(name="cronos_settimana", arguments={})
```

Pass `data` with any date in the target week to look at a past week instead.

**Check the month at a glance.** To see which artifacts exist for each day in a month (`raw.md`, `todo.md`, `fine-giornata.md`), call [`cronos_lista_mese`](#cronos_lista_mese):

```python
Tool(name="cronos_lista_mese", arguments={"mese": 6, "anno": 2026})
```

The entry count per day is shown for days whose main file is readable. This is the fastest way to spot days you forgot to close.

**Search across the full diary.** To find every diary entry mentioning a keyword, ticket, or pattern, call [`cronos_cerca`](#cronos_cerca):

```python
Tool(name="cronos_cerca", arguments={
    "query": "ABC-123",
    "ultimi_giorni": 90
})
```

The `query` field supports regular expressions. Narrow the scope with `tipo` (`"raw"`, `"todo"`, `"chiusura"`) when you only want to search one source type.

#### Projects and analytics

Use these tools to understand how time was spent, reconstruct project histories, and trace references across the diary.

**List active projects.** To see every project mentioned in the last 30 days (or any period), with occurrence counts and first/last dates, call [`cronos_lista_progetti`](#cronos_lista_progetti):

```python
Tool(name="cronos_lista_progetti", arguments={"ultimi_giorni": 30})
```

When a project registry is configured, names are resolved to their canonical form and grouped by parent system.

**Get the full story of a project.** To reconstruct the chronological timeline of work on `Alpha`, including aggregated Jira tickets, branches, and per-component entry counts, call [`cronos_progetto`](#cronos_progetto):

```python
Tool(name="cronos_progetto", arguments={"progetto": "Alpha", "ultimi_giorni": 90})
```

If `Alpha` is a system in the registry (with components underneath it), the tool rolls up all components automatically and sets `e_sistema: true` in the response. This is the tool for "tell me the story of Alpha" or "what is still open on Alpha".

**Analyse where time went.** To see the work distribution across projects and systems over a period, call [`cronos_statistiche`](#cronos_statistiche):

```python
Tool(name="cronos_statistiche", arguments={"ultimi_giorni": 90})
```

The `per_sistema` block shows each system's share of total entries (`quota_pct`). The `copertura` block tells you what fraction of your entries actually map to a registered project — `voci_mappate` vs `voci_totali` — so you can tell at a glance whether the registry covers your real work or has gaps.

**Trace a ticket or MR across the diary.** To find every diary entry that mentions ticket `ABC-123`, MR `!456`, or repository `api-gateway`, call [`cronos_riferimento`](#cronos_riferimento):

```python
Tool(name="cronos_riferimento", arguments={"riferimento": "ABC-123", "ultimi_giorni": 180})
```

The response gives you the full chronological thread with one snippet per match, plus the projects and systems the reference spans. Use this when a ticket lasted weeks and you need to reconstruct what happened and when.

#### Setup and maintenance

Use these tools once to bootstrap the project registry and then periodically to keep the diary clean.

**Bootstrap the project registry.** After writing several weeks of diary entries, call [`cronos_audit_progetti`](#cronos_audit_progetti) to scan all headings, cluster spelling variants, and generate a ready-to-paste `[cronos.projects]` draft:

```python
Tool(name="cronos_audit_progetti", arguments={"ultimi_giorni": 180})
```

The `bozza_toml` field in the response is valid TOML you can copy directly into `cronos.toml`. Add `sistema` fields where you want hierarchy. Re-run whenever the diary has grown and new project names have appeared.

**Check diary hygiene.** To detect structural problems — unmapped entries, unclosed code fences, missing working days, days that were never closed — call [`cronos_igiene`](#cronos_igiene):

```python
Tool(name="cronos_igiene", arguments={"ultimi_giorni": 180})
```

Each problem comes with a `gravita` level (`critico`, `avviso`, `info`) and an actionable `suggerimento`. A `critico` unclosed code fence will silently corrupt all analysis tools for that day and should be fixed immediately. Run `cronos_igiene` regularly (weekly or after adding new projects) to keep the diary in good shape.

**Consolidate a fragmented day.** If a day's `raw.md` has duplicate or scattered entries for the same project, call [`cronos_consolida_diario`](#cronos_consolida_diario) to get analysis and rewriting instructions:

```python
Tool(name="cronos_consolida_diario", arguments={"data": "2026-06-27"})
```

The tool is read-only: it returns instructions for the AI assistant to rewrite the file coherently. You review the proposed content before any write happens.

### Tools

#### `cronos_aggiungi_entry`

Add a new entry to the daily diary. Creates the file and year/month directory structure if they do not exist.

**Required parameters:**
- `progetto` (string): Project name (e.g. `"Backend API"`, `"Mobile App"`)
- `descrizione` (string): Short description of the work done (e.g. `"Fix auth bug"`)

**Optional parameters:**
- `paragrafo_intro` (string): Introductory paragraph summarising what was done (optional)
- `contenuto` (string): Additional content — sub-sections, bullet points, code
- `richiesto_da` (string): Name of the person who requested the work
- `repository` (string): Repository name — auto-detected from git when omitted
- `branch` (string): Branch name — auto-detected from git when omitted
- `working_dir` (string): Git working directory to auto-detect repository and branch from when not provided (optional)
- `jira_ticket` (string): Jira ticket code (e.g. `"SMART-123"`)
- `jira_url` (string): Jira ticket URL
- `gitlab_mr` (string): GitLab MR number (e.g. `"!456"`)
- `gitlab_mr_url` (string): GitLab MR URL
- `data` (string): Date in `YYYY-MM-DD` format (default: today)

When `repository` or `branch` are omitted, the tool attempts to detect them from the git repository found in `working_dir` (or the current working directory if `working_dir` is not provided).

**Returns:** Confirmation with file path and entry details.

---

#### `cronos_leggi_diario`

Read diary content for a date or date range. All parameters are optional; when none are supplied the tool returns today's diary.

**Parameters (mutually exclusive, use one):**
- `data` (string): Single date `YYYY-MM-DD`
- `data_inizio` + `data_fine` (strings): Date range `YYYY-MM-DD`
- `ultimi_giorni` (integer): Read the last N days

**Returns:** Diary content. `giorni` lists only days with content; `riepilogo` reports `files_trovati`, `files_mancanti`, and `date_mancanti` (dates with no file).

---

#### `cronos_imposta_bloccanti`

Set or update the Blockers section of a diary file. The file must already exist (use `cronos_aggiungi_entry` to create it).

**Required parameters:**
- `bloccanti` (string): Blocker text. Use `"None"` / `"Nessuno"` when there are no blockers.

**Optional parameters:**
- `data` (string): Date `YYYY-MM-DD` (default: today)

**Returns:** Confirmation with file path.

---

#### `cronos_riassunto_standup`

Generate a narrative, high-level standup summary. The tool returns the raw diary content together with style instructions so that the AI assistant can produce a fluent, professional standup message free of implementation details.

**Optional parameters:**
- `data` (string): Single date `YYYY-MM-DD` (default: last working day)
- `data_inizio` (string): Range start `YYYY-MM-DD`
- `data_fine` (string): Range end `YYYY-MM-DD`

**Returns:** Diary content with style instructions for message generation.

---

#### `cronos_fine_giornata`

End-of-day workflow trigger. Reads the day's raw entries and returns detailed instructions for generating four structured outputs: rewritten entries, a day summary, a technical summary, and a standup message.

**Optional parameters:**
- `data` (string): Date `YYYY-MM-DD` (default: today)

**Returns:** Raw diary entries with generation instructions.

---

#### `cronos_consolida_diario`

Consolidate the diary by merging fragmented or duplicate entries. The tool reads the current file, identifies structural issues, and returns instructions for rewriting it coherently.

**Optional parameters:**
- `data` (string): Date `YYYY-MM-DD` (default: today)

**Returns:** File content with analysis and consolidation instructions.

---

#### `cronos_lista_progetti`

List all projects mentioned in the diary over a given period. When a project registry is configured, names are resolved to their canonical form and grouped by parent system.

**Optional parameters:**
- `data_inizio` (string): Start date `YYYY-MM-DD`
- `data_fine` (string): End date `YYYY-MM-DD`
- `ultimi_giorni` (integer): Number of days to analyse (default: 30)
- `max_progetti` (integer): Maximum number of projects returned, ordered by frequency descending (default: 100)

**Returns:** `progetti` (each entry has `nome`, `sistema`, `occorrenze`, `prima_data`, `ultima_data`), `per_sistema` (occurrence rollup by parent system), `totale_progetti`, `max_progetti`, `troncato`.

---

#### `cronos_audit_progetti`

Scan diary headings over a period, cluster raw project names by normalised key, and return a ready-to-edit `[cronos.projects]` draft (`bozza_toml`). Read-only: it never writes `cronos.toml`.

Use this tool to bootstrap the project registry from an existing diary, discover spelling variants of the same project (e.g. `"WebApp"` / `"webapp"` / `"Web App"`), or get a starting point for configuring aliases and system hierarchy.

**Optional parameters:**
- `data_inizio` (string): Range start `YYYY-MM-DD`
- `data_fine` (string): Range end `YYYY-MM-DD`
- `ultimi_giorni` (integer): Days to scan when no dates are specified (default: 180)
- `max_voci` (integer): Maximum number of clusters returned (default: 200)

**Returns:** List of clusters (key, proposed canonical, variants, occurrences), a `bozza_toml` ready to paste, and an operational note.

---

#### `cronos_progetto`

Reconstruct the full story of a project or a system (with automatic component roll-up) from the diary: a chronological timeline, aggregated references (repository/branch/Jira/MR), per-component entry counts, and per-day blockers. Read-only, with a capped output to keep responses concise.

Use this tool when you want to answer "tell me the story of project X", "what have I done on X and what is still open?", or "dossier of Backend API".

**Required parameters:**
- `progetto` (string): Project or system name (e.g. `"Backend API"`, `"Platform"`)

**Optional parameters:**
- `data_inizio` (string): Range start `YYYY-MM-DD`
- `data_fine` (string): Range end `YYYY-MM-DD`
- `ultimi_giorni` (integer): Days to analyse when no dates are specified (default: 180)
- `max_voci` (integer): Maximum number of timeline entries returned; oldest entries are dropped first when the limit is exceeded (default: 50)

**Returns:** A dossier dict with:
- `e_sistema` (bool): whether the requested name resolves to a system rather than a single component
- `membri` (list or null): components belonging to the system, when `e_sistema` is true
- `timeline` (list): chronological diary entries, capped to `max_voci`
- `riferimenti` (dict): deduplicated references aggregated across all entries (repositories, branches, Jira tickets, MRs)
- `per_progetto` (dict): entry count per component, sorted by frequency descending
- `bloccanti` (list): per-day blocker texts (only days with actual blockers)
- `troncato` (bool): true when the timeline was truncated

**Example:**

```python
Tool(name="cronos_progetto", arguments={"progetto": "Backend API", "ultimi_giorni": 90})
```

Returns the last 90 days of diary activity on `Backend API`, with aggregated branch and Jira references, per-component breakdown, and any recorded blockers.

---

#### `cronos_statistiche`

Show work distribution by project and system over a period. Read-only, with a capped output to keep responses concise. Effort is a proxy (entry count and distinct days), not manual time-tracking.

Use this tool when you want to answer "where did the month go?", "how did I split my time across projects?", or "work distribution for the last quarter".

**Optional parameters:**
- `data_inizio` (string): Start date `YYYY-MM-DD`
- `data_fine` (string): End date `YYYY-MM-DD`
- `ultimi_giorni` (integer): Days to analyse when no dates are specified (default: 90)
- `max_progetti` (integer): Maximum number of projects returned, ordered by entry count descending (default: 50)

**Returns:**
- `totali`: `voci` (total entry count), `giorni_attivi` (days with at least one entry), `progetti` (distinct project count), `sistemi` (distinct system count)
- `copertura`: how much of the written work these stats actually see — `voci_totali` (every H3 entry), `voci_mappate` (those resolving to a registered project), `voci_non_mappate`, `percentuale`, and `registro_attivo`. With an empty registry everything maps (100%). `voci_non_mappate` includes both untagged work and sub-section headings written as H3, so the percentage is a lower bound on real coverage, not an accusation.
- `per_sistema`: per-system roll-up, each entry has `sistema`, `voci`, `giorni`, `quota_pct` (share of total entries, %)
- `per_progetto`: per-project detail with `nome`, `sistema`, `voci`, `giorni`
- `per_mese`: month-by-month activity trend (entry count per month, `YYYY-MM` keys)
- `troncato`: true when the project list was capped at `max_progetti`

**Example:**

```python
Tool(name="cronos_statistiche", arguments={"ultimi_giorni": 90})
```

Returns the last 90 days of diary activity: how many entries were logged per project and per system, each system's share of the total workload, and a month-by-month entry trend. With a project registry configured (e.g. `api-gateway` and `billing` both under system `"Platform"`), the `per_sistema` roll-up shows the combined weight of `Platform` as a single line with its `quota_pct`.

---

#### `cronos_riferimento`

Reconstruct the thread of a reference (ticket, MR, or repo) across the diary: every entry that mentions it, in chronological order, tagged with its canonical project, plus the projects and systems the reference spans. Read-only, capped output.

Use this tool when you want to answer "everything that touches PROJ-123", "the thread of MR !456", "where did I work on the Backend API repo", or "trace PROJ-123".

**Required parameters:**
- `riferimento` (string): Ticket / MR / repo / string to trace (e.g. `"PROJ-123"`, `"Backend API"`)

**Optional parameters:**
- `data_inizio` (string): Range start `YYYY-MM-DD`
- `data_fine` (string): Range end `YYYY-MM-DD`
- `ultimi_giorni` (integer): Days to analyse when no dates are specified (default: 180)
- `max_voci` (integer): Maximum number of timeline entries returned (default: 50)

**Returns:**
- `progetti` (list): canonical project names that mention the reference
- `sistemi` (list): system names that mention the reference (via project registry roll-up)
- `timeline` (list): chronological diary entries, capped to `max_voci`; each item has `data`, `progetto`, `titolo`, `snippet`
- `num_voci` (int): total number of matches found before capping
- `num_giorni` (int): number of distinct days with at least one match
- `prima_data` / `ultima_data` (string or null): first and last date of a match
- `troncato` (bool): true when the timeline was truncated at `max_voci`

**Example:**

```python
Tool(name="cronos_riferimento", arguments={"riferimento": "PROJ-123", "ultimi_giorni": 180})
```

Returns the last 180 days of diary entries that mention `PROJ-123`, grouped by canonical project, with the list of projects and systems involved and a per-entry snippet showing the matching context.

---

#### `cronos_igiene`

Read-only diary hygiene advisor. Scans the diary over a period and reports hygiene problems with a severity level and an actionable suggestion for each one, plus a human-readable one-line summary. Never writes any file.

Four checks are performed:

- **`voci_non_mappate`** (severity: `avviso`) — entry headings that do not map to any registered project, aggregated as a single finding with the total count, the number of affected days, and a few example headings. These entries are invisible to `cronos_progetto` and `cronos_statistiche`. Delegates the grouped breakdown to `cronos_audit_progetti`. Skipped when the registry is empty.
- **`fence_non_chiusa`** (severity: `critico`) — an unclosed fenced code block at end of a day file; all later entries in that file merge into the open block and disappear from analysis tools.
- **`giorno_lavorativo_mancante`** (severity: `info`) — a working day (holiday-aware) with no diary file at all.
- **`chiusura_mancante`** (severity: `info`) — a day that has a `raw.md` but no `fine-giornata.md`. Legacy single-file days are excluded.

**Optional parameters:**
- `data_inizio` (string): Range start `YYYY-MM-DD`
- `data_fine` (string): Range end `YYYY-MM-DD`
- `ultimi_giorni` (integer): Days to analyse when no dates are specified (default: 180)
- `max_problemi` (integer): Maximum number of problems in the output list (default: 100); per-type and per-severity counts always reflect the full total

**Returns:**

```json
{
  "periodo": {"da": "2026-04-01", "a": "2026-06-28", "giorni_analizzati": 88},
  "registro_attivo": true,
  "riepilogo": "5 problemi: 0 critici, 1 avvisi, 4 info — 12 voci fuori registro (in 4 giorni), 3 giorni feriali senza diario, 1 giornata non chiusa.",
  "problemi": [
    {"tipo": "voci_non_mappate", "gravita": "avviso", "data": null,
     "voci": 12, "giorni": 4, "esempi": ["Code Review MR #42", "Rebase branch X"],
     "dettaglio": "12 voci in 4 giorni non mappano ad alcun progetto del registro",
     "suggerimento": "Lancia cronos_audit_progetti per vederle raggruppate e decidere cosa aggiungere a [cronos.projects]."},
    {"tipo": "giorno_lavorativo_mancante", "gravita": "info", "data": "2026-05-04",
     "dettaglio": "giorno lavorativo senza diario",
     "suggerimento": "Se era una giornata di ferie/malattia ignora; altrimenti il giorno non e' tracciato."}
  ],
  "conteggi": {"voci_non_mappate": 1, "fence_non_chiusa": 0, "giorno_lavorativo_mancante": 3, "chiusura_mancante": 1},
  "conteggi_gravita": {"critico": 0, "avviso": 1, "info": 4},
  "totale_problemi": 5, "max_problemi": 100, "troncato": false, "note": []
}
```

The `riepilogo` field is a human-readable Italian string (the tool's output strings are Italian by design). `registro_attivo` is false when no `[cronos.projects]` section is configured, in which case the `voci_non_mappate` check is skipped and a note is added. `troncato` is true when `totale_problemi` exceeds `max_problemi`; the counts are always the full totals regardless.

---

#### `cronos_cerca`

Full-text search across diary sources (raw entries, todo files, end-of-day files). Case-insensitive, with regex support.

**Required parameters:**
- `query` (string): Text to search for (supports regular expressions)

**Optional parameters:**
- `data_inizio` (string): Search range start `YYYY-MM-DD`
- `data_fine` (string): Search range end `YYYY-MM-DD`
- `ultimi_giorni` (integer): Days to search (default: 90)
- `tipo` (list[str]): Sources to search — `"raw"`, `"todo"`, `"chiusura"`. Default: all three.
- `max_risultati` (int): Maximum number of results returned (default 50).

**Returns:** Total match count (`totale_risultati`), a `troncato` flag and `max_risultati` limit, and `risultati` (at most `max_risultati` matches, each with type, date, and context).

---

#### `cronos_settimana`

Weekly summary of the diary grouped by project. Shows how many days each project was worked on during the week, with an activity overview.

**Optional parameters:**
- `data` (string): Any date within the week to analyse `YYYY-MM-DD` (default: current week)

**Returns:** Per-project summary with day count, dates, and activities.

---

#### `cronos_aggiungi_a_progetto`

Append a sub-section (H4) to an existing project entry in today's diary. Avoids fragmentation when logging multiple work sessions on the same project. If no matching project entry is found, a new standard entry is created instead.

**Required parameters:**
- `progetto` (string): Exact project name as it appears in the existing H3 heading
- `titolo_fase` (string): Sub-section title (e.g. `"Fix login bug"`)
- `contenuto` (string): Sub-section content

**Optional parameters:**
- `richiesto_da` (string): Name of the person who requested the work
- `repository` (string): Repository name — auto-detected from git when omitted
- `branch` (string): Branch name — auto-detected from git when omitted
- `working_dir` (string): Git working directory to auto-detect repository and branch from when not provided (optional)
- `jira_ticket` (string): Jira ticket code
- `jira_url` (string): Jira ticket URL
- `gitlab_mr` (string): GitLab MR number
- `gitlab_mr_url` (string): GitLab MR URL
- `data` (string): Date `YYYY-MM-DD` (default: today)

When `repository` or `branch` are omitted, the tool attempts to detect them from the git repository found in `working_dir` (or the current working directory if `working_dir` is not provided).

**Returns:** Confirmation with mode (`aggiunto_a_esistente` or `nuova_entry`).

---

#### `cronos_scrivi_fine_giornata`

Write the end-of-day file with the fully generated content. Use this tool after `cronos_fine_giornata`: first generate the content following the returned instructions, then call this tool to persist it.

**Required parameters:**
- `contenuto` (string): Complete markdown content for the end-of-day file

**Optional parameters:**
- `data` (string): Date `YYYY-MM-DD` (default: today)
- `contenuto_todo` (string): If provided, prepares the next working day's folder with this todo.md after writing (optional)

**Returns:** Confirmation with the written file path. When `contenuto_todo` is given, the result also includes a `prepara_domani` section with the paths of the next day's `todo.md` and `raw.md`.

---

#### `cronos_leggi_todo`

Read the `todo.md` for a given day. Useful for answering "what was I supposed to do today?". If a `todo.bak.md` backup exists in the same folder (created by a previous `cronos_prepara_domani` overwrite), its path is reported alongside the main content.

**Optional parameters:**
- `data` (string): Date `YYYY-MM-DD` (default: today)

**Returns:** Content of `todo.md`, its file path, and optional backup info.

---

#### `cronos_lista_mese`

Month dashboard: one row per day showing which artifacts exist (legacy single-file, `raw.md`, `todo.md`, `fine-giornata.md`) and the entry count for days whose main file is readable.

**Optional parameters:**
- `mese` (integer): Month number 1–12 (default: current month)
- `anno` (integer): Year `YYYY` (default: current year)

**Returns:** Totals summary plus per-day detail with artifact presence flags.

---

#### `cronos_prepara_domani`

Prepare the next working day's folder. By default the target date is calculated as the next working day from today (Mon–Thu → +1 day, Fri/Sat/Sun → Monday). An explicit date can be provided to plan any future day.

Behaviour:
- Creates or overwrites `todo.md` with `contenuto_todo` (a todo is the latest plan, not a running log; any existing `todo.md` is backed up to `todo.bak.md`).
- Creates `raw.md` with the standard skeleton **only if it does not already exist**, to avoid overwriting entries added in advance.

**Required parameters:**
- `contenuto_todo` (string): Complete markdown content for `todo.md`

**Optional parameters:**
- `data` (string): Target date `YYYY-MM-DD` (default: next working day)

**Returns:** Confirmation with paths of `todo.md` and `raw.md`, and a flag indicating whether `raw.md` was created.

---

### Diary Format

#### File Structure

Diary files are organised in a year/month hierarchy under the diary root:

```
Diary/
├── cronos.toml
├── templates/
└── {year}/
    └── {month}/
        ├── {year}-{month}-{day}.md        (legacy single-file, historical)
        └── {year}-{month}-{day}/          (current per-day folder)
            ├── raw.md            progressive daily log
            ├── fine-giornata.md  end-of-day closure
            └── todo.md           day's to-do list
```

Days that already have a legacy single file keep using it without migration; new days use the per-day folder.

#### Markdown Format

```markdown
# For Stand-up - April 9, 2025

## What I did yesterday

### ProjectName - Short description

Introductory paragraph summarising what was accomplished.

#### Sub-section (optional)

- Detail point 1
- Detail point 2

**References:**
- Repository: repo-name
- Branch: `branch-name`
- Jira: [TICKET-123](https://your.jira/browse/TICKET-123)
- GitLab MR: [MR !456](https://gitlab.example.com/project/-/merge_requests/456)

---

## Blockers

None
```

### Languages

Built-in language packs: **Italian** (`it`, default) and **English** (`en`). Set via `cronos.toml`:

```toml
[cronos]
lang = "en"
```

Section headings, month names, weekday names, title format, and default blocker text are all localised automatically when the language is switched.

---

## Italiano

### Funzionalita'

- **Aggiunta entry**: Aggiunge nuove entry al diario giornaliero, creando file e cartelle automaticamente
- **Lettura diario**: Legge le entry per data singola, range di date o ultimi N giorni
- **Riassunto standup**: Genera un riassunto narrativo ad alto livello pronto per gli standup
- **Gestione bloccanti**: Imposta e aggiorna la sezione Bloccanti di qualsiasi file del diario
- **Workflow fine giornata**: Riscrive e ristruttura le entry del giorno, genera riassunto giornata, riassunto tecnico e messaggio standup
- **Consolidamento diario**: Unisce entry frammentate o duplicate in un file coerente
- **Lista progetti**: Elenca tutti i progetti su cui si e' lavorato in un periodo
- **Ricerca full-text**: Cerca nel diario con supporto regex
- **Report settimanale**: Riassume la settimana raggruppato per progetto
- **Aggiungi a progetto**: Aggiunge una sotto-sezione a un'entry di progetto esistente senza frammentazione
- **Scrivi file fine giornata**: Persiste il contenuto strutturato di fine giornata su disco
- **Lettura todo**: Legge il `todo.md` di un determinato giorno (cosa era pianificato)
- **Dashboard mensile**: Vista del mese a colpo d'occhio: quali artefatti esistono per ogni giorno
- **Prepara domani**: Crea la cartella del prossimo giorno lavorativo con todo e scheletro raw
- **Internazionalizzazione**: Pacchetti lingua italiano e inglese integrati, configurabili via `cronos.toml`
- **Commit Git**: Commit automatico (e push opzionale) del diario a fine giornata
- **Metadati di riferimento**: Repository, branch, ticket Jira e MR GitLab sono registrati sulle entry come riferimenti testuali — usati per ricerca e roll-up. Cronos **non** chiama le API di Jira o GitLab: nessuna integrazione live.

### Installazione

```bash
pip install mcp-cronos
```

Oppure con `uv`:

```bash
uv add mcp-cronos
```

### Configurazione

#### Claude Code (`settings.json`)

Aggiungi al file di configurazione di Claude Code (tipicamente `~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "cronos": {
      "command": "uvx",
      "args": ["mcp-cronos"],
      "env": {
        "CRONOS_DIARIO_PATH": "/percorso/al/tuo/Diario"
      }
    }
  }
}
```

Se stai eseguendo da un checkout locale invece del pacchetto pubblicato:

```json
{
  "mcpServers": {
    "cronos": {
      "command": "uv",
      "args": [
        "--directory",
        "/percorso/a/Cronos",
        "run",
        "mcp-cronos"
      ],
      "env": {
        "CRONOS_DIARIO_PATH": "/percorso/al/tuo/Diario"
      }
    }
  }
}
```

La variabile d'ambiente `CRONOS_DIARIO_PATH` e' obbligatoria. Deve puntare alla directory radice del diario.

#### `cronos.toml`

Posiziona un file `cronos.toml` nella directory radice del diario (ovvero `$CRONOS_DIARIO_PATH/cronos.toml`), oppure in `~/.config/cronos/cronos.toml`. Un percorso esplicito puo' essere impostato tramite la variabile d'ambiente `CRONOS_CONFIG_PATH`.

Tutte le impostazioni sono opzionali e usano i valori predefiniti della lingua quando omesse.

```toml
[cronos]
# Lingua: "it" (predefinito) o "en"
lang = "it"

[cronos.sections]
# Sovrascrive le etichette delle sezioni usate nei file del diario.
# Devono corrispondere agli heading presenti nei file esistenti se si sta
# migrando dalle etichette predefinite in italiano.
entries         = "Cosa ho fatto ieri"
blockers        = "Bloccanti"
day_summary     = "Riassunto della giornata"
tech_summary    = "Riassunto tecnico"
standup_message = "Messaggio per lo standup"

[cronos.diary]
# Stringa di formato per il titolo del file. Supporta il placeholder {date}.
title_format = "Per lo Stand-up - {date}"

[cronos.git]
# Abilita commit git automatico a fine giornata (predefinito: true)
enabled = true
# Push dopo il commit (predefinito: true)
auto_push = true
# Template del messaggio di commit. Supporta il placeholder {date}.
commit_message = "diario: fine giornata {date}"

[cronos.calendar]
# Codice paese ISO per il calendario festivi nazionale (default "IT").
country = "IT"
# Date extra trattate come festive (ponti, chiusure aziendali), YYYY-MM-DD.
extra_holidays = ["2026-12-07"]
```

Il calcolo del prossimo/precedente giorno lavorativo usato da `cronos_prepara_domani` e dal riassunto standup esclude i festivi nazionali del paese configurato piu' le `extra_holidays`, oltre ai weekend.

#### Registry dei progetti (opzionale)

Il registry dei progetti e' completamente opzionale. Cronos funziona senza alcuna configurazione dei progetti, e nessun nome di progetto e' hardcoded nel pacchetto.

Quando si vuole una vista a due livelli sistema → componente e un'identita' canonica dei progetti tra varianti di scrittura, si aggiunge una sezione `[cronos.projects]` al proprio `cronos.toml`:

```toml
[cronos.projects.api-gateway]
sistema = "Platform"
alias = ["APIGateway", "api gw"]

[cronos.projects.billing]
sistema = "Platform"
```

Ogni `[cronos.projects.<name>]` dichiara un `sistema` padre opzionale (il gruppo o area prodotto a cui il componente appartiene) e sinonimi `alias` opzionali. Le varianti di maiuscolo, spaziatura e punteggiatura sono riconosciute automaticamente, quindi `alias` serve solo per nomi genuinamente diversi, non per `"API Gateway"` vs `"api gateway"`.

Il modo piu' semplice per costruire questa lista e' eseguire `cronos_audit_progetti`, che scansiona le intestazioni del diario e restituisce una bozza `bozza_toml` pronta, raggruppata per chiave normalizzata. Basta copiare quella bozza nel proprio `cronos.toml`, aggiungere `sistema` dove si vuole la gerarchia, e il gioco e' fatto.

#### Template Personalizzati

I file template per l'output generato (file di fine giornata, messaggio standup, ecc.) possono essere posizionati in una sottodirectory `templates/` all'interno della radice del diario. Quando presenti, questi sovrascrivono i valori predefiniti integrati. Il server carica i template da `$CRONOS_DIARIO_PATH/templates/` automaticamente.

### Per iniziare

Il modo piu' semplice per passare da un diario grezzo a un registry dei progetti funzionante e' un ciclo in due passi: `cronos_audit_progetti` costruisce la lista, `cronos_igiene` la mantiene.

1. **Scrivi le entry del diario come al solito**, usando intestazioni del tipo `### NomeProgetto - Breve descrizione`.
2. **Esegui `cronos_audit_progetti`**: scansiona le intestazioni del diario, raggruppa le varianti di scrittura e produce una bozza `[cronos.projects]` pronta da incollare (`bozza_toml`).
3. **Incolla la bozza nel `cronos.toml`** (in `$CRONOS_DIARIO_PATH/cronos.toml`). Aggiungi un campo `sistema` dove vuoi la gerarchia, ritocca gli alias se necessario: il tool fa il lavoro di raggruppamento al posto tuo.
4. **Esegui `cronos_igiene`**: verifica che ogni intestazione risolva a un progetto registrato, segnala i giorni lavorativi senza diario, le fence di codice non chiuse e le giornate mai chiuse. Segui i suggerimenti per tenere il diario pulito.

Ripeti il passo 4 ogni volta che aggiungi nuovi progetti o noti lacune. Riesegui il passo 2 quando il diario e' cresciuto e sono comparsi nomi di progetto non ancora nel registry.

### Guida all'uso

Questa sezione e' una guida pratica ai casi d'uso, organizzata per obiettivo. Ogni ricetta indica quale tool chiamare e con quali argomenti chiave; i parametri completi non vengono ripetuti qui — per le firme complete consulta il [riferimento Tool](#tool) qui sotto. Parti da questa sezione quando vuoi ottenere un risultato; vai al riferimento quando hai bisogno del nome esatto di un parametro o dei dettagli del valore di ritorno.

#### Durante la giornata

Questi tool servono a catturare il lavoro man mano che avviene, aggiungere contesto alle entry esistenti, annotare i bloccanti e verificare cosa era pianificato.

**Registra un'attivita'.** Per tracciare cosa hai fatto su un progetto, chiama [`cronos_aggiungi_entry`](#cronos_aggiungi_entry):

```python
Tool(name="cronos_aggiungi_entry", arguments={
    "progetto": "Alpha",
    "descrizione": "fix redirect login",
    "jira_ticket": "ABC-123"
})
```

Crea il file del diario di oggi (e la cartella anno/mese) se non esistono, e aggiunge un'entry `### Alpha - fix redirect login`. Ometti `jira_ticket` quando non c'e' un ticket; fornisci `repository` e `branch` esplicitamente oppure lascia che il tool li rilevi da git.

**Aggiungi una seconda sessione allo stesso progetto senza frammentare.** Se hai lavorato di nuovo su `Alpha` nel corso della giornata, appendi una sotto-sezione invece di creare un secondo heading duplicato, usando [`cronos_aggiungi_a_progetto`](#cronos_aggiungi_a_progetto):

```python
Tool(name="cronos_aggiungi_a_progetto", arguments={
    "progetto": "Alpha",
    "titolo_fase": "code review",
    "contenuto": "Revisionata PR !42 — lasciati due commenti sulla gestione degli errori."
})
```

Il tool trova l'heading `### Alpha` esistente e aggiunge un blocco `#### code review` sotto di esso. Se non trova un heading corrispondente, crea una nuova entry standard.

**Registra un bloccante.** Una volta che il file del diario di oggi esiste, imposta la sezione Bloccanti con [`cronos_imposta_bloccanti`](#cronos_imposta_bloccanti):

```python
Tool(name="cronos_imposta_bloccanti", arguments={
    "bloccanti": "In attesa del sign-off del team Beta sul contratto API."
})
```

Richiamalo piu' tardi con `"Nessuno"` per aggiornarlo quando il bloccante e' risolto.

**Controlla cosa era pianificato.** Per leggere la lista dei todo di oggi (o di qualsiasi giorno), chiama [`cronos_leggi_todo`](#cronos_leggi_todo):

```python
Tool(name="cronos_leggi_todo", arguments={})
```

Se una precedente esecuzione di [`cronos_prepara_domani`](#cronos_prepara_domani) ha salvato un backup del piano precedente, il suo path viene riportato insieme al contenuto corrente.

#### Chiudere la giornata

La chiusura e' deliberatamente un flusso in due fasi. `cronos_fine_giornata` legge le entry grezze e restituisce le istruzioni di generazione; l'assistente AI redige poi il contenuto strutturato; infine `cronos_scrivi_fine_giornata` lo persiste su disco. Tieni le due chiamate separate — non unirle in un unico passo.

**Fase 1 — avvia il workflow di fine giornata.** Chiama [`cronos_fine_giornata`](#cronos_fine_giornata) per ricevere il diario grezzo e le istruzioni per generare i quattro output strutturati (entry riscritte, riassunto della giornata, riassunto tecnico, messaggio standup):

```python
Tool(name="cronos_fine_giornata", arguments={})
```

Segui le istruzioni restituite per redigere il contenuto. In questa fase stai costruendo la narrativa, non stai ancora scrivendo su disco.

**Fase 2 — persisti il file generato.** Quando il contenuto e' pronto, chiama [`cronos_scrivi_fine_giornata`](#cronos_scrivi_fine_giornata) per scrivere `fine-giornata.md`. Opzionalmente passa una bozza di todo per il giorno successivo nella stessa chiamata, evitando un passo separato con [`cronos_prepara_domani`](#cronos_prepara_domani):

```python
Tool(name="cronos_scrivi_fine_giornata", arguments={
    "contenuto": "... contenuto markdown completo ...",
    "contenuto_todo": "## Domani\n- Revisionare spec API Beta\n- Implementazione ABC-124"
})
```

Quando `contenuto_todo` e' fornito, `todo.md` e lo scheletro `raw.md` del prossimo giorno lavorativo vengono creati automaticamente.

**Prepara il giorno dopo separatamente.** Se preferisci pianificare il domani come passo dedicato (per esempio dopo uno standup in cui le priorita' sono cambiate), chiama [`cronos_prepara_domani`](#cronos_prepara_domani) da solo:

```python
Tool(name="cronos_prepara_domani", arguments={
    "contenuto_todo": "## 2026-07-01\n- Implementazione ABC-124\n- Deploy su staging"
})
```

Il tool calcola automaticamente il prossimo giorno lavorativo, escludendo weekend e festivi. Fornisci `data` esplicita per pianificare un giorno futuro specifico.

**Genera il messaggio per lo standup.** Per produrre un messaggio di standup narrativo e professionale dal diario di ieri (o da qualsiasi data), chiama [`cronos_riassunto_standup`](#cronos_riassunto_standup):

```python
Tool(name="cronos_riassunto_standup", arguments={})
```

Il tool restituisce il contenuto grezzo del diario insieme a istruzioni di stile affinche' l'assistente AI produca un messaggio fluido, privo di dettagli implementativi. Fornisci `data_inizio` e `data_fine` per coprire un arco di piu' giorni (per esempio dopo un weekend lungo).

#### Rileggere il diario

Questi tool servono a recuperare quanto scritto, che si tratti di un singolo giorno, una settimana, un mese o una ricerca mirata.

**Leggi un giorno o un intervallo.** Chiama [`cronos_leggi_diario`](#cronos_leggi_diario) senza argomenti per il diario di oggi, con una data singola, un range di date o gli ultimi N giorni:

```python
# Oggi
Tool(name="cronos_leggi_diario", arguments={})

# Un giorno specifico
Tool(name="cronos_leggi_diario", arguments={"data": "2026-06-20"})

# Ultimi 5 giorni
Tool(name="cronos_leggi_diario", arguments={"ultimi_giorni": 5})
```

Il campo `riepilogo` nella risposta riporta le date prive di file, in modo da individuare le lacune a colpo d'occhio.

**Panoramica settimanale.** Per vedere la settimana corrente raggruppata per progetto (quanti giorni e' stato attivo ciascun progetto e cosa e' stato fatto), chiama [`cronos_settimana`](#cronos_settimana):

```python
Tool(name="cronos_settimana", arguments={})
```

Passa `data` con qualsiasi data nella settimana target per guardare una settimana passata.

**Controlla il mese a colpo d'occhio.** Per vedere quali artefatti esistono per ogni giorno di un mese (`raw.md`, `todo.md`, `fine-giornata.md`), chiama [`cronos_lista_mese`](#cronos_lista_mese):

```python
Tool(name="cronos_lista_mese", arguments={"mese": 6, "anno": 2026})
```

Il conteggio delle entry per giorno e' visibile per i giorni con file principale leggibile. E' il modo piu' rapido per individuare le giornate mai chiuse.

**Ricerca in tutto il diario.** Per trovare ogni entry che menziona una parola chiave, un ticket o uno schema, chiama [`cronos_cerca`](#cronos_cerca):

```python
Tool(name="cronos_cerca", arguments={
    "query": "ABC-123",
    "ultimi_giorni": 90
})
```

Il campo `query` supporta espressioni regolari. Restringi l'ambito con `tipo` (`"raw"`, `"todo"`, `"chiusura"`) quando vuoi cercare solo in una sorgente.

#### Progetti e analisi

Questi tool servono a capire come e' stato distribuito il tempo, ricostruire la storia dei progetti e tracciare riferimenti nel diario.

**Elenca i progetti attivi.** Per vedere ogni progetto menzionato negli ultimi 30 giorni (o qualsiasi periodo), con conteggio occorrenze e date di prima/ultima attivita', chiama [`cronos_lista_progetti`](#cronos_lista_progetti):

```python
Tool(name="cronos_lista_progetti", arguments={"ultimi_giorni": 30})
```

Quando e' configurato un registry dei progetti, i nomi vengono risolti nella forma canonica e raggruppati per sistema padre.

**Ricostruisci la storia di un progetto.** Per ricostruire la timeline cronologica del lavoro su `Alpha`, inclusi ticket Jira aggregati, branch e conteggio entry per componente, chiama [`cronos_progetto`](#cronos_progetto):

```python
Tool(name="cronos_progetto", arguments={"progetto": "Alpha", "ultimi_giorni": 90})
```

Se `Alpha` e' un sistema nel registry (con componenti sotto di esso), il tool fa il roll-up automatico e imposta `e_sistema: true` nella risposta. Usa questo tool per "raccontami la storia di Alpha" o "cosa e' rimasto aperto su Alpha".

**Analizza dove e' andato il tempo.** Per vedere la distribuzione del lavoro tra progetti e sistemi in un periodo, chiama [`cronos_statistiche`](#cronos_statistiche):

```python
Tool(name="cronos_statistiche", arguments={"ultimi_giorni": 90})
```

Il blocco `per_sistema` mostra la quota di ogni sistema sul totale delle entry (`quota_pct`). Il blocco `copertura` indica quale frazione delle entry mappa realmente a un progetto registrato — `voci_mappate` vs `voci_totali` — cosi' capisci immediatamente se il registry copre il lavoro reale o ha lacune.

**Traccia un ticket o una MR nel diario.** Per trovare ogni entry che menziona il ticket `ABC-123`, la MR `!456` o il repository `api-gateway`, chiama [`cronos_riferimento`](#cronos_riferimento):

```python
Tool(name="cronos_riferimento", arguments={"riferimento": "ABC-123", "ultimi_giorni": 180})
```

La risposta restituisce il thread cronologico completo con uno snippet per ogni match, piu' i progetti e i sistemi che il riferimento attraversa. Usalo quando un ticket e' durato settimane e devi ricostruire cosa e' successo e quando.

#### Configurazione e manutenzione

Questi tool si usano una volta sola per costruire il registry dei progetti e poi periodicamente per tenere il diario in ordine.

**Bootstrap del registry dei progetti.** Dopo aver scritto alcune settimane di entry, chiama [`cronos_audit_progetti`](#cronos_audit_progetti) per scansionare tutte le intestazioni, raggruppare le varianti di scrittura e generare una bozza `[cronos.projects]` pronta da incollare:

```python
Tool(name="cronos_audit_progetti", arguments={"ultimi_giorni": 180})
```

Il campo `bozza_toml` nella risposta e' TOML valido che puoi copiare direttamente nel `cronos.toml`. Aggiungi i campi `sistema` dove vuoi la gerarchia. Riesegui quando il diario e' cresciuto e sono comparsi nuovi nomi di progetto.

**Controlla l'igiene del diario.** Per rilevare problemi strutturali — entry non mappate, fence di codice non chiuse, giorni lavorativi mancanti, giornate mai chiuse — chiama [`cronos_igiene`](#cronos_igiene):

```python
Tool(name="cronos_igiene", arguments={"ultimi_giorni": 180})
```

Ogni problema ha un livello `gravita` (`critico`, `avviso`, `info`) e un `suggerimento` azionabile. Una fence non chiusa con gravita' `critico` corrompe silenziosamente tutti i tool di analisi per quel giorno e va corretta subito. Esegui `cronos_igiene` regolarmente (ogni settimana o dopo aver aggiunto nuovi progetti) per mantenere il diario in buono stato.

**Consolida una giornata frammentata.** Se il `raw.md` di un giorno ha entry duplicate o sparse per lo stesso progetto, chiama [`cronos_consolida_diario`](#cronos_consolida_diario) per ottenere analisi e istruzioni di riscrittura:

```python
Tool(name="cronos_consolida_diario", arguments={"data": "2026-06-27"})
```

Il tool e' read-only: restituisce le istruzioni affinche' l'assistente AI riscriva il file in modo coerente. Puoi rivedere il contenuto proposto prima che venga scritto qualsiasi file.

### Tool

#### `cronos_aggiungi_entry`

Aggiunge una nuova entry al diario giornaliero. Crea il file e la struttura di directory anno/mese se non esistono.

**Parametri obbligatori:**
- `progetto` (string): Nome del progetto (es. `"Backend API"`, `"Mobile App"`)
- `descrizione` (string): Breve descrizione del lavoro svolto (es. `"Fix bug autenticazione"`)

**Parametri opzionali:**
- `paragrafo_intro` (string): Paragrafo introduttivo che riassume cosa e' stato fatto (opzionale)
- `contenuto` (string): Contenuto aggiuntivo — sottosezioni, elenchi puntati, codice
- `richiesto_da` (string): Nome della persona che ha richiesto il lavoro
- `repository` (string): Nome del repository — rilevato automaticamente da git se omesso
- `branch` (string): Nome del branch — rilevato automaticamente da git se omesso
- `working_dir` (string): Directory di lavoro git da cui rilevare repository e branch se non forniti (opzionale)
- `jira_ticket` (string): Codice ticket Jira (es. `"SMART-123"`)
- `jira_url` (string): URL del ticket Jira
- `gitlab_mr` (string): Numero MR GitLab (es. `"!456"`)
- `gitlab_mr_url` (string): URL della MR GitLab
- `data` (string): Data nel formato `YYYY-MM-DD` (predefinito: oggi)

Quando `repository` o `branch` sono omessi, il tool tenta di rilevarli dal repository git trovato in `working_dir` (oppure dalla directory di lavoro corrente se `working_dir` non e' fornita).

**Restituisce:** Conferma con path del file e dettagli dell'entry.

---

#### `cronos_leggi_diario`

Legge il contenuto del diario per una data o un range di date. Tutti i parametri sono opzionali; se nessuno viene fornito restituisce il diario di oggi.

**Parametri (mutualmente esclusivi, usarne uno):**
- `data` (string): Data singola `YYYY-MM-DD`
- `data_inizio` + `data_fine` (string): Range di date `YYYY-MM-DD`
- `ultimi_giorni` (integer): Legge gli ultimi N giorni

**Restituisce:** Contenuto del diario. `giorni` elenca solo i giorni con contenuto; `riepilogo` riporta `files_trovati`, `files_mancanti` e `date_mancanti` (le date prive di file).

---

#### `cronos_imposta_bloccanti`

Imposta o aggiorna la sezione Bloccanti di un file del diario. Il file deve esistere (usare `cronos_aggiungi_entry` per crearlo).

**Parametri obbligatori:**
- `bloccanti` (string): Testo dei bloccanti. Usare `"Nessuno"` quando non ci sono bloccanti.

**Parametri opzionali:**
- `data` (string): Data `YYYY-MM-DD` (predefinito: oggi)

**Restituisce:** Conferma con path del file.

---

#### `cronos_riassunto_standup`

Genera un riassunto discorsivo ad alto livello per lo standup. Il tool restituisce il contenuto grezzo del diario insieme a istruzioni di stile affinche' l'assistente AI produca un messaggio fluido e professionale privo di dettagli implementativi.

**Parametri opzionali:**
- `data` (string): Data singola `YYYY-MM-DD` (predefinito: ultimo giorno lavorativo)
- `data_inizio` (string): Inizio range `YYYY-MM-DD`
- `data_fine` (string): Fine range `YYYY-MM-DD`

**Restituisce:** Contenuto del diario con istruzioni di stile per la generazione del messaggio.

---

#### `cronos_fine_giornata`

Avvia il workflow di fine giornata. Legge le entry grezze del giorno e restituisce istruzioni dettagliate per generare quattro output strutturati: entry riscritte, riassunto della giornata, riassunto tecnico e messaggio per lo standup.

**Parametri opzionali:**
- `data` (string): Data `YYYY-MM-DD` (predefinito: oggi)

**Restituisce:** Entry grezze del diario con istruzioni di generazione.

---

#### `cronos_consolida_diario`

Consolida il diario unendo entry frammentate o duplicate. Il tool rilegge il file corrente, identifica i problemi di struttura e restituisce istruzioni per riscriverlo in modo coerente.

**Parametri opzionali:**
- `data` (string): Data `YYYY-MM-DD` (predefinito: oggi)

**Restituisce:** Contenuto del file con analisi e istruzioni per il consolidamento.

---

#### `cronos_lista_progetti`

Elenca tutti i progetti menzionati nel diario in un dato periodo. Se e' presente un registry dei progetti, i nomi vengono risolti nella loro forma canonica e raggruppati per sistema padre.

**Parametri opzionali:**
- `data_inizio` (string): Data inizio `YYYY-MM-DD`
- `data_fine` (string): Data fine `YYYY-MM-DD`
- `ultimi_giorni` (integer): Numero di giorni da analizzare (predefinito: 30)
- `max_progetti` (integer): Numero massimo di progetti restituiti, ordinati per frequenza decrescente (predefinito: 100)

**Restituisce:** `progetti` (ogni voce ha `nome`, `sistema`, `occorrenze`, `prima_data`, `ultima_data`), `per_sistema` (rollup occorrenze per sistema padre), `totale_progetti`, `max_progetti`, `troncato`.

---

#### `cronos_audit_progetti`

Scansiona le intestazioni del diario su un periodo, raggruppa i nomi grezzi dei progetti per chiave normalizzata, e restituisce una bozza `[cronos.projects]` pronta da modificare (`bozza_toml`). Read-only: non scrive mai `cronos.toml`.

Utile per costruire il registry dei progetti da un diario esistente, scoprire varianti di scrittura dello stesso progetto (es. `"WebApp"` / `"webapp"` / `"Web App"`), o avere una base di partenza per configurare alias e gerarchia dei sistemi.

**Parametri opzionali:**
- `data_inizio` (string): Inizio range `YYYY-MM-DD`
- `data_fine` (string): Fine range `YYYY-MM-DD`
- `ultimi_giorni` (integer): Giorni da scansionare se non si specificano le date (predefinito: 180)
- `max_voci` (integer): Numero massimo di cluster restituiti (predefinito: 200)

**Restituisce:** Lista cluster (chiave, canonico proposto, varianti, occorrenze), una `bozza_toml` pronta da incollare e una nota operativa.

---

#### `cronos_progetto`

Ricostruisce la storia completa di un progetto o di un sistema (con roll-up automatico dei componenti) dal diario: timeline cronologica, riferimenti aggregati (repository/branch/Jira/MR), conteggio per componente e bloccanti per giorno. Read-only, con output limitato per mantenere le risposte concise.

Usare questo tool quando si vuole rispondere a "raccontami la storia del progetto X", "cosa ho fatto su X e cosa e' rimasto aperto?" oppure "dossier di Backend API".

**Parametri obbligatori:**
- `progetto` (string): Nome del progetto o sistema (es. `"Backend API"`, `"Platform"`)

**Parametri opzionali:**
- `data_inizio` (string): Inizio range `YYYY-MM-DD`
- `data_fine` (string): Fine range `YYYY-MM-DD`
- `ultimi_giorni` (integer): Giorni da analizzare se le date non sono specificate (predefinito: 180)
- `max_voci` (integer): Numero massimo di voci nella timeline; le voci piu' vecchie vengono eliminate per prime quando il limite viene superato (predefinito: 50)

**Restituisce:** Un dossier dict con:
- `e_sistema` (bool): indica se il nome richiesto risolve a un sistema anziche' a un singolo componente
- `membri` (list o null): componenti appartenenti al sistema, quando `e_sistema` e' true
- `timeline` (list): entry del diario in ordine cronologico, troncate a `max_voci`
- `riferimenti` (dict): riferimenti deduplicati aggregati su tutte le entry (repository, branch, ticket Jira, MR)
- `per_progetto` (dict): conteggio entry per componente, ordinato per frequenza decrescente
- `bloccanti` (list): testi dei bloccanti per giorno (solo i giorni con bloccanti reali)
- `troncato` (bool): true quando la timeline e' stata troncata

**Esempio:**

```python
Tool(name="cronos_progetto", arguments={"progetto": "Backend API", "ultimi_giorni": 90})
```

Restituisce gli ultimi 90 giorni di attivita' del diario su `Backend API`, con riferimenti aggregati a branch e ticket Jira, ripartizione per componente e i bloccanti registrati.

---

#### `cronos_statistiche`

Mostra la distribuzione del lavoro per progetto e per sistema in un periodo. Read-only, con output limitato per mantenere le risposte concise. Lo sforzo e' un proxy (conteggio voci e giorni distinti), non un time-tracking manuale.

Usare questo tool quando si vuole rispondere a "dove e' andato il mese?", "come ho distribuito il tempo tra i progetti?" o "distribuzione del lavoro nell'ultimo trimestre".

**Parametri opzionali:**
- `data_inizio` (string): Data inizio `YYYY-MM-DD`
- `data_fine` (string): Data fine `YYYY-MM-DD`
- `ultimi_giorni` (integer): Giorni da analizzare se le date non sono specificate (predefinito: 90)
- `max_progetti` (integer): Numero massimo di progetti restituiti, ordinati per numero di voci decrescente (predefinito: 50)

**Restituisce:**
- `totali`: `voci` (totale entry), `giorni_attivi` (giorni con almeno una entry), `progetti` (progetti distinti), `sistemi` (sistemi distinti)
- `copertura`: quanto del lavoro scritto queste statistiche vedono davvero — `voci_totali` (ogni voce H3), `voci_mappate` (quelle che risolvono a un progetto del registry), `voci_non_mappate`, `percentuale` e `registro_attivo`. Con registry vuoto tutto mappa (100%). `voci_non_mappate` include sia il lavoro non taggato sia i sotto-titoli scritti come H3, quindi la percentuale e' un limite inferiore della copertura reale, non un'accusa.
- `per_sistema`: roll-up per sistema; ogni voce ha `sistema`, `voci`, `giorni`, `quota_pct` (quota percentuale sul totale delle voci)
- `per_progetto`: dettaglio per progetto con `nome`, `sistema`, `voci`, `giorni`
- `per_mese`: trend di attivita' per mese (conteggio voci per mese, chiavi `YYYY-MM`)
- `troncato`: true quando la lista dei progetti e' stata troncata a `max_progetti`

**Esempio:**

```python
Tool(name="cronos_statistiche", arguments={"ultimi_giorni": 90})
```

Restituisce gli ultimi 90 giorni di attivita' del diario: quante entry per progetto e per sistema, la quota percentuale di ciascun sistema sul totale e il trend mensile delle voci. Con un registry configurato (es. `api-gateway` e `billing` entrambi sotto il sistema `"Platform"`), il roll-up `per_sistema` mostra il peso complessivo di `Platform` come singola riga con la relativa `quota_pct`.

---

#### `cronos_riferimento`

Ricostruisce il filo di un riferimento (ticket, MR o repo) nel diario: ogni entry che lo menziona, in ordine cronologico, con il progetto canonico, piu' i progetti e i sistemi coinvolti. Read-only, con output limitato per mantenere le risposte concise.

Usare questo tool quando si vuole rispondere a "tutto cio' che tocca PROJ-123", "il filo della MR !456", "dove ho lavorato sul repo Backend API" o "traccia PROJ-123".

**Parametri obbligatori:**
- `riferimento` (string): Ticket / MR / repo / stringa da tracciare (es. `"PROJ-123"`, `"Backend API"`)

**Parametri opzionali:**
- `data_inizio` (string): Inizio range `YYYY-MM-DD`
- `data_fine` (string): Fine range `YYYY-MM-DD`
- `ultimi_giorni` (integer): Giorni da analizzare se le date non sono specificate (predefinito: 180)
- `max_voci` (integer): Numero massimo di voci nella timeline (predefinito: 50)

**Restituisce:**
- `progetti` (list): nomi dei progetti canonici che menzionano il riferimento
- `sistemi` (list): nomi dei sistemi che menzionano il riferimento (tramite roll-up del registry)
- `timeline` (list): entry del diario in ordine cronologico, troncate a `max_voci`; ogni voce ha `data`, `progetto`, `titolo`, `snippet`
- `num_voci` (int): numero totale di match trovati prima del troncamento
- `num_giorni` (int): numero di giorni distinti con almeno un match
- `prima_data` / `ultima_data` (string o null): prima e ultima data di un match
- `troncato` (bool): true quando la timeline e' stata troncata a `max_voci`

**Esempio:**

```python
Tool(name="cronos_riferimento", arguments={"riferimento": "PROJ-123", "ultimi_giorni": 180})
```

Restituisce gli ultimi 180 giorni di entry del diario che menzionano `PROJ-123`, raggruppate per progetto canonico, con la lista dei progetti e dei sistemi coinvolti e uno snippet per voce che mostra il contesto del match.

---

#### `cronos_igiene`

Advisor di igiene del diario, sola lettura. Scansiona il diario su un periodo e segnala i problemi di igiene con un livello di gravita' e un suggerimento azionabile per ciascuno, piu' un riepilogo umano in una riga. Non scrive mai alcun file.

Vengono eseguiti quattro controlli:

- **`voci_non_mappate`** (gravita': `avviso`) — intestazioni di voce che non mappano ad alcun progetto del registry, aggregate in un unico risultato con il totale, il numero di giorni coinvolti e alcune intestazioni di esempio. Queste voci sono invisibili a `cronos_progetto` e `cronos_statistiche`. Delega la ripartizione raggruppata a `cronos_audit_progetti`. Saltato quando il registry e' vuoto.
- **`fence_non_chiusa`** (gravita': `critico`) — blocco di codice fenced non chiuso a fine file giornata; tutte le voci successive si fondono nel blocco aperto e spariscono dagli strumenti di analisi.
- **`giorno_lavorativo_mancante`** (gravita': `info`) — giorno lavorativo (festivo-aware) senza alcun file del diario.
- **`chiusura_mancante`** (gravita': `info`) — giorno con `raw.md` ma senza `fine-giornata.md`. I giorni legacy single-file sono esclusi.

**Parametri opzionali:**
- `data_inizio` (string): Inizio range `YYYY-MM-DD`
- `data_fine` (string): Fine range `YYYY-MM-DD`
- `ultimi_giorni` (integer): Giorni da analizzare se le date non sono specificate (predefinito: 180)
- `max_problemi` (integer): Numero massimo di problemi nell'elenco di output (predefinito: 100); i conteggi per tipo e per gravita' riflettono sempre il totale reale

**Restituisce:**

```json
{
  "periodo": {"da": "2026-04-01", "a": "2026-06-28", "giorni_analizzati": 88},
  "registro_attivo": true,
  "riepilogo": "5 problemi: 0 critici, 1 avvisi, 4 info — 12 voci fuori registro (in 4 giorni), 3 giorni feriali senza diario, 1 giornata non chiusa.",
  "problemi": [
    {"tipo": "voci_non_mappate", "gravita": "avviso", "data": null,
     "voci": 12, "giorni": 4, "esempi": ["Code Review MR #42", "Rebase branch X"],
     "dettaglio": "12 voci in 4 giorni non mappano ad alcun progetto del registro",
     "suggerimento": "Lancia cronos_audit_progetti per vederle raggruppate e decidere cosa aggiungere a [cronos.projects]."},
    {"tipo": "giorno_lavorativo_mancante", "gravita": "info", "data": "2026-05-04",
     "dettaglio": "giorno lavorativo senza diario",
     "suggerimento": "Se era una giornata di ferie/malattia ignora; altrimenti il giorno non e' tracciato."}
  ],
  "conteggi": {"voci_non_mappate": 1, "fence_non_chiusa": 0, "giorno_lavorativo_mancante": 3, "chiusura_mancante": 1},
  "conteggi_gravita": {"critico": 0, "avviso": 1, "info": 4},
  "totale_problemi": 5, "max_problemi": 100, "troncato": false, "note": []
}
```

`registro_attivo` e' false quando non e' configurata nessuna sezione `[cronos.projects]`; in quel caso il controllo `voci_non_mappate` e' saltato e viene aggiunta una nota. `troncato` e' true quando `totale_problemi` supera `max_problemi`; i conteggi sono sempre i totali reali indipendentemente dal troncamento.

---

#### `cronos_cerca`

Ricerca full-text nelle sorgenti del diario (entry raw, file todo, file di chiusura). Case-insensitive, con supporto regex.

**Parametri obbligatori:**
- `query` (string): Testo da cercare (supporta espressioni regolari)

**Parametri opzionali:**
- `data_inizio` (string): Inizio range di ricerca `YYYY-MM-DD`
- `data_fine` (string): Fine range di ricerca `YYYY-MM-DD`
- `ultimi_giorni` (integer): Giorni da cercare (predefinito: 90)
- `tipo` (list[str]): Sorgenti da cercare — `"raw"`, `"todo"`, `"chiusura"`. Default: tutte e tre.
- `max_risultati` (int): Numero massimo di risultati restituiti (default 50).

**Restituisce:** Numero totale di match (`totale_risultati`), flag `troncato` e limite `max_risultati`, e `risultati` (al massimo `max_risultati` match, ciascuno con tipo, data e contesto).

---

#### `cronos_settimana`

Riassunto settimanale del diario raggruppato per progetto. Mostra su quanti giorni si e' lavorato per ogni progetto durante la settimana, con riepilogo delle attivita'.

**Parametri opzionali:**
- `data` (string): Qualsiasi data nella settimana da analizzare `YYYY-MM-DD` (predefinito: settimana corrente)

**Restituisce:** Riassunto per progetto con numero di giorni, date e attivita'.

---

#### `cronos_aggiungi_a_progetto`

Aggiunge una sotto-sezione (H4) a un'entry di progetto esistente nel diario di oggi. Evita la frammentazione quando si registrano piu' sessioni di lavoro sullo stesso progetto. Se non viene trovata una entry corrispondente, viene creata una nuova entry standard.

**Parametri obbligatori:**
- `progetto` (string): Nome esatto del progetto come appare nell'heading H3 esistente
- `titolo_fase` (string): Titolo della sotto-sezione (es. `"Fix bug login"`)
- `contenuto` (string): Contenuto della sotto-sezione

**Parametri opzionali:**
- `richiesto_da` (string): Nome della persona che ha richiesto il lavoro
- `repository` (string): Nome del repository — rilevato automaticamente da git se omesso
- `branch` (string): Nome del branch — rilevato automaticamente da git se omesso
- `working_dir` (string): Directory di lavoro git da cui rilevare repository e branch se non forniti (opzionale)
- `jira_ticket` (string): Codice ticket Jira
- `jira_url` (string): URL del ticket Jira
- `gitlab_mr` (string): Numero MR GitLab
- `gitlab_mr_url` (string): URL della MR GitLab
- `data` (string): Data `YYYY-MM-DD` (predefinito: oggi)

Quando `repository` o `branch` sono omessi, il tool tenta di rilevarli dal repository git trovato in `working_dir` (oppure dalla directory di lavoro corrente se `working_dir` non e' fornita).

**Restituisce:** Conferma con modalita' (`aggiunto_a_esistente` o `nuova_entry`).

---

#### `cronos_scrivi_fine_giornata`

Scrive il file di fine giornata con il contenuto generato. Usare questo tool DOPO `cronos_fine_giornata`: prima generare il contenuto seguendo le istruzioni ricevute, poi chiamare questo tool per persistere il risultato.

**Parametri obbligatori:**
- `contenuto` (string): Contenuto markdown completo del file di fine giornata

**Parametri opzionali:**
- `data` (string): Data `YYYY-MM-DD` (predefinito: oggi)
- `contenuto_todo` (string): Se fornito, dopo la scrittura prepara la cartella del prossimo giorno lavorativo con questo todo.md (opzionale)

**Restituisce:** Conferma con path del file scritto. Quando `contenuto_todo` e' fornito, il risultato include anche una sezione `prepara_domani` con i path di `todo.md` e `raw.md` del giorno successivo.

---

#### `cronos_leggi_todo`

Legge il file `todo.md` di una data. Utile per rispondere alla domanda "cosa dovevo fare oggi?". Se nella stessa cartella esiste un `todo.bak.md` (creato da una ripianificazione precedente con `cronos_prepara_domani`), il path del backup viene riportato insieme al contenuto principale.

**Parametri opzionali:**
- `data` (string): Data `YYYY-MM-DD` (predefinito: oggi)

**Restituisce:** Contenuto di `todo.md`, path del file e info eventuale sul backup.

---

#### `cronos_lista_mese`

Dashboard mensile: un record per giorno con l'indicazione di quali artefatti sono presenti (legacy single-file, `raw.md`, `todo.md`, `fine-giornata.md`) e il numero di entry per i giorni con file principale leggibile.

**Parametri opzionali:**
- `mese` (integer): Numero mese 1-12 (predefinito: mese corrente)
- `anno` (integer): Anno `YYYY` (predefinito: anno corrente)

**Restituisce:** Riepilogo totali e dettaglio per giorno con flag di presenza degli artefatti.

---

#### `cronos_prepara_domani`

Prepara la cartella del prossimo giorno lavorativo. Per default il giorno target e' calcolato come prossimo giorno lavorativo da oggi (lun-gio → +1 giorno, ven/sab/dom → lunedi'). E' possibile specificare una data esplicita per pianificare un qualsiasi giorno futuro.

Comportamento:
- Crea o sovrascrive `todo.md` con `contenuto_todo` (un todo e' l'ultima pianificazione, non un log progressivo; l'eventuale `todo.md` esistente viene salvato come `todo.bak.md`).
- Crea `raw.md` con lo scheletro standard **solo se non esiste gia'**, per non sovrascrivere entry aggiunte in anticipo.

**Parametri obbligatori:**
- `contenuto_todo` (string): Contenuto markdown completo di `todo.md`

**Parametri opzionali:**
- `data` (string): Data target `YYYY-MM-DD` (predefinito: prossimo giorno lavorativo)

**Restituisce:** Conferma con path di `todo.md` e `raw.md`, e flag che indica se `raw.md` e' stato creato.

---

### Formato Diario

#### Struttura File

I file del diario sono organizzati in una gerarchia anno/mese sotto la directory radice:

```
Diario/
├── cronos.toml
├── templates/
└── {anno}/
    └── {mese}/
        ├── {anno}-{mese}-{giorno}.md        (legacy single-file, storico)
        └── {anno}-{mese}-{giorno}/          (cartella per-giorno, attuale)
            ├── raw.md            log progressivo giornaliero
            ├── fine-giornata.md  chiusura di fine giornata
            └── todo.md           lista delle cose da fare
```

I giorni che hanno gia' un file legacy continuano a usarlo senza migrazione; i nuovi giorni usano la cartella per-giorno.

#### Formato Markdown

```markdown
# Per lo Stand-up - 9 Aprile 2025

## Cosa ho fatto ieri

### NomeProgetto - Breve descrizione

Paragrafo introduttivo che riassume cosa e' stato realizzato.

#### Sottosezione (opzionale)

- Punto di dettaglio 1
- Punto di dettaglio 2

**Riferimenti:**
- Repository: nome-repository
- Branch: `nome-branch`
- Jira: [TICKET-123](https://your.jira/browse/TICKET-123)
- Gitlab Mr: [MR !456](https://gitlab.esempio.it/progetto/-/merge_requests/456)

---

## Bloccanti

Nessuno
```

### Lingue

Pacchetti lingua integrati: **Italiano** (`it`, predefinito) e **Inglese** (`en`). Si imposta via `cronos.toml`:

```toml
[cronos]
lang = "it"
```

Intestazioni di sezione, nomi dei mesi, nomi dei giorni della settimana, formato del titolo e testo predefinito dei bloccanti sono tutti localizzati automaticamente al cambio della lingua.

---

## License

MIT
