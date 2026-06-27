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
- **Git integration**: Automatic commit (and optional push) at end-of-day

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

### Tools

#### `cronos_aggiungi_entry`

Add a new entry to the daily diary. Creates the file and year/month directory structure if they do not exist.

**Required parameters:**
- `progetto` (string): Project name (e.g. `"SmarTicket"`, `"MCP Cronos"`)
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

Use this tool to bootstrap the project registry from an existing diary, discover spelling variants of the same project (e.g. `"PayGW"` / `"PayGw"` / `"Pay GW"`), or get a starting point for configuring aliases and system hierarchy.

**Optional parameters:**
- `data_inizio` (string): Range start `YYYY-MM-DD`
- `data_fine` (string): Range end `YYYY-MM-DD`
- `ultimi_giorni` (integer): Days to scan when no dates are specified (default: 180)
- `max_voci` (integer): Maximum number of clusters returned (default: 200)

**Returns:** List of clusters (key, proposed canonical, variants, occurrences), a `bozza_toml` ready to paste, and an operational note.

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
- **Integrazione Git**: Commit automatico (e push opzionale) a fine giornata

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

### Tool

#### `cronos_aggiungi_entry`

Aggiunge una nuova entry al diario giornaliero. Crea il file e la struttura di directory anno/mese se non esistono.

**Parametri obbligatori:**
- `progetto` (string): Nome del progetto (es. `"SmarTicket"`, `"MCP Cronos"`)
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

Utile per costruire il registry dei progetti da un diario esistente, scoprire varianti di scrittura dello stesso progetto (es. `"PayGW"` / `"PayGw"` / `"Pay GW"`), o avere una base di partenza per configurare alias e gerarchia dei sistemi.

**Parametri opzionali:**
- `data_inizio` (string): Inizio range `YYYY-MM-DD`
- `data_fine` (string): Fine range `YYYY-MM-DD`
- `ultimi_giorni` (integer): Giorni da scansionare se non si specificano le date (predefinito: 180)
- `max_voci` (integer): Numero massimo di cluster restituiti (predefinito: 200)

**Restituisce:** Lista cluster (chiave, canonico proposto, varianti, occorrenze), una `bozza_toml` pronta da incollare e una nota operativa.

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
