# Identita' di progetto (fondazione D) — Piano di implementazione

> **Per worker agentici:** SUB-SKILL RICHIESTA: superpowers:subagent-driven-development. Step a checkbox (`- [ ]`).

**Goal:** dare a Cronos un'identita' di progetto canonica, calcolata a lettura sopra il markdown, con modello a due livelli sistema->componente opt-in, generica e multi-utente.

**Architettura:** nuovo modulo `utils/projects.py` con funzioni pure (`normalize_project`, `project_tokens`) e risolutori che leggono il registro da config (`canonical_projects`, `system_of`). Un registro `[cronos.projects]` in `cronos.toml` (vuoto di default) abilita whitelist e gerarchia; senza registro vale solo il parsing migliorato. `extract_projects`, `lista_progetti` e un nuovo `cronos_audit_progetti` usano questi risolutori.

**Tech Stack:** Python 3.10+, tomllib, pytest, ruff.

**Riferimento spec:** `docs/specs/2026-06-14-project-identity-design.md`

## Global Constraints
- Codice/commenti/docstring/commit in inglese; piano/spec in italiano.
- PEP8, 100 col, doppi apici, ruff pulito; zero test falliti.
- **Zero specificita' di dominio nel pacchetto**: nessun nome di progetto reale nel codice; tutto nel `cronos.toml` dell'utente.
- **Non distruttivo**: i file del diario non vengono mai riscritti.
- **Opt-in / degrado elegante**: con registro vuoto Cronos funziona come oggi piu' il parsing migliorato; whitelist e gerarchia solo a registro popolato.
- Niente import circolari: `utils/projects.py` NON importa `config` a livello di modulo; i risolutori fanno l'import di `load_config` in modo lazy dentro la funzione. `config.py` importa solo `normalize_project` da `utils/projects.py`.

---

## Task 1: Registro a due livelli in config

**Files:**
- Modify: `src/mcp_cronos/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `normalize_project` da `utils/projects.py` (Task 2). NOTA d'ordine: Task 2 introduce `normalize_project`; per non bloccare, in QUESTO task definisci una `normalize_project` minima in `utils/projects.py` (solo la funzione pura, vedi sotto) e il resto del modulo lo completa Task 2. Quindi Task 1 crea `utils/projects.py` con la sola `normalize_project`.
- Produces: `CronosConfig.project_canonical: dict[str, str]` (chiave-normalizzata -> nome canonico), `CronosConfig.project_system: dict[str, str]` (canonico -> sistema), `CronosConfig.projects_registered: bool`.

- [ ] **Step 1: creare `utils/projects.py` con la funzione pura `normalize_project`**

```python
"""Project-identity helpers: normalization and canonical resolution.

The diary stores plain markdown; project identity is resolved at read time
against an optional [cronos.projects] registry. With an empty registry the
helpers fall back to improved parsing only (em-dash, composites), so the tool
works out-of-the-box for any user. No domain specifics live here.
"""

import re
from typing import Optional


def normalize_project(name: str) -> str:
    """Return a match key for a project name.

    Lowercases, drops parenthetical suffixes like "(BDI)", and removes every
    non-alphanumeric character so that case, spacing and punctuation variants
    collapse: "PayGW"/"PayGw"/"Pay GW" -> "paygw",
    "Beacon Service"/"BeaconService" -> "beaconservice". Genuinely different
    synonyms still need an explicit alias in the registry.
    """
    s = name.strip().lower()
    s = re.sub(r"\s*\([^)]*\)", "", s)  # drop parentheticals
    s = re.sub(r"[^0-9a-z]+", "", s)  # keep alphanumerics only
    return s
```

- [ ] **Step 2: test che fallisce (config)**

Append a `tests/test_config.py`:

```python
def test_config_projects_empty_by_default(tmp_diario):
    from mcp_cronos.config import load_config

    config = load_config()
    assert config.projects_registered is False
    assert config.project_canonical == {}
    assert config.project_system == {}


def test_config_projects_registry(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n'
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\n\n'
        '[cronos.projects.PayGW]\nsistema = "Teseo"\nalias = ["PayGw"]\n\n'
        '[cronos.projects.Teseo]\nalias = ["Teseo Infra"]\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config, load_config

    _reset_config()
    config = load_config()

    assert config.projects_registered is True
    # canonical maps its own normalized form
    assert config.project_canonical["smarticket"] == "SmarTicket"
    assert config.project_canonical["paygw"] == "PayGW"
    # alias normalized -> canonical
    assert config.project_canonical["paygw"] == "PayGW"  # "PayGw" normalizes to same key
    assert config.project_canonical["teseoinfra"] == "Teseo"
    # system mapping for components only
    assert config.project_system["SmarTicket"] == "Teseo"
    assert config.project_system["PayGW"] == "Teseo"
    assert "Teseo" not in config.project_system
```

Run: `uv run pytest tests/test_config.py -k projects -v` → FAIL.

- [ ] **Step 3: aggiungere i campi a `CronosConfig`**

In `CronosConfig`, dopo `commit_message: str`, aggiungere:

```python
    project_canonical: dict[str, str]
    project_system: dict[str, str]
    projects_registered: bool
```

- [ ] **Step 4: parsare `[cronos.projects]` in `load_config`**

In cima a `config.py`, fra gli import, aggiungere:

```python
from mcp_cronos.utils.projects import normalize_project
```

In `load_config`, subito prima della costruzione `_config = CronosConfig(...)`, aggiungere:

```python
    # Project registry (optional, two-level system->component). Empty by default:
    # an empty registry leaves project handling in pass-through mode.
    raw_projects: dict[str, Any] = cronos_section.get("projects", {})
    project_canonical: dict[str, str] = {}
    project_system: dict[str, str] = {}
    for canonical, meta in raw_projects.items():
        project_canonical[normalize_project(canonical)] = canonical
        if isinstance(meta, dict):
            for alias in meta.get("alias", []) or []:
                project_canonical[normalize_project(str(alias))] = canonical
            sistema = meta.get("sistema")
            if sistema:
                project_system[canonical] = str(sistema)
    projects_registered = len(raw_projects) > 0
```

E nel costruttore `_config = CronosConfig(...)`, dopo `commit_message=commit_message,`:

```python
        project_canonical=project_canonical,
        project_system=project_system,
        projects_registered=projects_registered,
```

- [ ] **Step 5: verificare**

Run: `uv run pytest tests/test_config.py -k projects -v` → PASS.
Run: `uv run pytest -q` → verde. `uv run ruff check src/mcp_cronos/config.py src/mcp_cronos/utils/projects.py tests/test_config.py` → pulito.

- [ ] **Step 6: commit**

```bash
git add src/mcp_cronos/config.py src/mcp_cronos/utils/projects.py tests/test_config.py
git commit -m "feat(config): add optional two-level project registry

CHANGE: Parses an optional [cronos.projects] registry into CronosConfig
(project_canonical alias->canonical index, project_system component->system,
projects_registered flag). Adds utils/projects.normalize_project. Empty by
default, no domain specifics in the package."
```

---

## Task 2: Risolutori di progetto (`utils/projects.py`)

**Files:**
- Modify: `src/mcp_cronos/utils/projects.py`
- Test: `tests/test_projects.py` (nuovo)

**Interfaces:**
- Consumes: `normalize_project` (Task 1); `load_config()` (lazy import) per `project_canonical`, `project_system`, `projects_registered`.
- Produces: `project_tokens(heading: str) -> list[str]`; `canonical_projects(heading: str) -> list[str]`; `system_of(canonical: str) -> Optional[str]`.

- [ ] **Step 1: test che fallisce (nuovo file)**

Creare `tests/test_projects.py`:

```python
"""Tests for mcp_cronos.utils.projects."""


def test_project_tokens_plain(tmp_diario):
    from mcp_cronos.utils.projects import project_tokens

    assert project_tokens("SmarTicket - Fix login") == ["SmarTicket"]


def test_project_tokens_emdash(tmp_diario):
    from mcp_cronos.utils.projects import project_tokens

    assert project_tokens("SmarTicket — Campo is_bookable (DVT-439)") == ["SmarTicket"]


def test_project_tokens_composite(tmp_diario):
    from mcp_cronos.utils.projects import project_tokens

    assert project_tokens("RapsodiaTrace / IoPollicino") == ["RapsodiaTrace", "IoPollicino"]


def test_project_tokens_keeps_internal_hyphen(tmp_diario):
    from mcp_cronos.utils.projects import project_tokens

    assert project_tokens("django-db-maintenance - release") == ["django-db-maintenance"]


def test_canonical_passthrough_when_no_registry(tmp_diario):
    # Empty registry: tokens pass through unchanged (improved parsing only).
    from mcp_cronos.utils.projects import canonical_projects

    assert canonical_projects("SmarTicket — desc") == ["SmarTicket"]
    assert canonical_projects("A / B") == ["A", "B"]


def test_canonical_resolves_and_filters_with_registry(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n'
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\nalias = ["BDI"]\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.projects import canonical_projects, system_of

    _reset_config()
    # variant by case/space resolves via normalization
    assert canonical_projects("smarticket - x") == ["SmarTicket"]
    # explicit alias resolves
    assert canonical_projects("BDI - y") == ["SmarTicket"]
    # unknown name is dropped (whitelist active because registry non-empty)
    assert canonical_projects("Totally Unknown Thing") == []
    # system lookup
    assert system_of("SmarTicket") == "Teseo"
    assert system_of("SomethingElse") is None
```

Run: `uv run pytest tests/test_projects.py -v` → FAIL.

- [ ] **Step 2: implementare i risolutori in `utils/projects.py`**

Aggiungere sotto `normalize_project`:

```python
_DESC_SEP = re.compile(r"\s[-—]\s")  # " - " or " — " separating project from description


def project_tokens(heading: str) -> list[str]:
    """Split a heading's project text into one or more display project tokens.

    Composites joined by " / " become multiple tokens; the description after
    a " - " or " — " separator is dropped. Internal hyphens without surrounding
    spaces (e.g. "django-db-maintenance") are preserved.
    """
    tokens: list[str] = []
    for part in heading.split(" / "):
        token = _DESC_SEP.split(part, maxsplit=1)[0].strip()
        if token:
            tokens.append(token)
    return tokens


def canonical_projects(heading: str) -> list[str]:
    """Resolve a heading's project text to canonical project names.

    With a populated registry, only names that resolve to a known canonical are
    returned (others are dropped as unclassified). With an empty registry, the
    cleaned tokens pass through unchanged. Composites yield multiple projects.
    """
    from mcp_cronos.config import load_config

    config = load_config()
    result: list[str] = []
    for token in project_tokens(heading):
        if config.projects_registered:
            canonical = config.project_canonical.get(normalize_project(token))
            if canonical is not None and canonical not in result:
                result.append(canonical)
        else:
            if token not in result:
                result.append(token)
    return result


def system_of(canonical: str) -> Optional[str]:
    """Return the parent system of a canonical component, or None."""
    from mcp_cronos.config import load_config

    return load_config().project_system.get(canonical)
```

- [ ] **Step 3: verificare**

Run: `uv run pytest tests/test_projects.py -v` → PASS.
Run: `uv run pytest -q` → verde. `uv run ruff check src/mcp_cronos/utils/projects.py tests/test_projects.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/utils/projects.py tests/test_projects.py
git commit -m "feat(projects): add token, canonical and system resolvers

CHANGE: project_tokens (em-dash/composite-aware), canonical_projects (registry
whitelist when populated, pass-through when empty), system_of. load_config is
imported lazily to avoid an import cycle with config."
```

---

## Task 3: `extract_projects` usa i risolutori

**Files:**
- Modify: `src/mcp_cronos/utils/markdown.py`
- Test: `tests/test_markdown.py`

**Interfaces:**
- Consumes: `canonical_projects` (Task 2).
- Produces: `extract_projects(content)` ora restituisce nomi canonici (o token passthrough), em-dash/composite-aware.

- [ ] **Step 1: test che fallisce**

Append a `tests/test_markdown.py`:

```python
def test_extract_projects_emdash_and_composite_no_registry(tmp_diario):
    from mcp_cronos.utils.markdown import extract_projects

    content = (
        "### SmarTicket — Campo is_bookable (DVT-439)\n\nx\n\n---\n\n"
        "### RapsodiaTrace / IoPollicino\n\ny\n"
    )
    projects = extract_projects(content)
    assert projects == ["SmarTicket", "RapsodiaTrace", "IoPollicino"]


def test_extract_projects_filters_with_registry(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n[cronos.projects.SmarTicket]\nsistema = "Teseo"\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.markdown import extract_projects

    _reset_config()
    content = "### SmarTicket - x\n\na\n\n---\n\n### Prossimi passi\n\nb\n"
    # "Prossimi passi" is not registered -> dropped; SmarTicket kept.
    assert extract_projects(content) == ["SmarTicket"]
```

Run: `uv run pytest tests/test_markdown.py -k extract_projects -v` → il secondo FALLISCE (oggi conta "Prossimi passi").

- [ ] **Step 2: reindirizzare `extract_projects`**

In `src/mcp_cronos/utils/markdown.py`, aggiungere l'import in cima (con gli altri import del package):

```python
from mcp_cronos.utils.projects import canonical_projects
```

Sostituire il corpo di `extract_projects` (mantenendo la segmentazione fence-aware):

```python
    projects: list[str] = []
    for part in _split_entries_respecting_fences(content):
        first_line = part.split("\n", 1)[0]
        if not first_line.startswith("### "):
            continue
        header = first_line[4:].strip()
        for project in canonical_projects(header):
            if project not in projects:
                projects.append(project)
    return projects
```

(Aggiornare il docstring: ora delega la risoluzione del nome a `canonical_projects`, quindi gestisce em-dash, composti e, a registro popolato, il filtro dei non classificati.)

- [ ] **Step 3: verificare**

Run: `uv run pytest tests/test_markdown.py -k extract_projects -v` → PASS.
Run: `uv run pytest -q` → verde (attenzione ai test esistenti di `lista_progetti`/`extract_projects`: con registro vuoto il comportamento resta equivalente, em-dash a parte). Se un test esistente si rompe per via dell'em-dash su un heading che prima finiva intero, valuta se e' il nuovo comportamento corretto; in caso di dubbio fermati e segnala.
Run: `uv run ruff check src/mcp_cronos/utils/markdown.py tests/test_markdown.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/utils/markdown.py tests/test_markdown.py
git commit -m "feat(markdown): resolve project names via canonical_projects

CHANGE: extract_projects now delegates name resolution to canonical_projects, so
it understands em-dash separators and composites, and filters unclassified
headings when a registry is configured. Fence-aware segmentation unchanged."
```

---

## Task 4: `lista_progetti` a due livelli e output cappato

**Files:**
- Modify: `src/mcp_cronos/tools/reader.py`
- Test: `tests/test_reader.py`

**Interfaces:**
- Consumes: `extract_projects` (Task 3), `system_of` (Task 2).
- Produces: nuovo output di `lista_progetti` con `progetti` (lista cappata di `{nome, sistema, occorrenze, prima_data, ultima_data}`), `per_sistema` (dict sistema->occorrenze), `totale_progetti`, `troncato`, `max_progetti`.

- [ ] **Step 1: test che fallisce**

In `tests/test_reader.py`, aggiungere (usa la fixture `sample_diary_it` che crea 2026-04-09 con entry "MCP Cronos" e "SmarTicket"):

```python
def test_lista_progetti_two_level_with_registry(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n[cronos.projects.SmarTicket]\nsistema = "Teseo"\n',
        encoding="utf-8",
    )
    month = tmp_diario / "2026" / "04"
    month.mkdir(parents=True, exist_ok=True)
    (month / "2026-04-09.md").write_text(
        "# Per lo Stand-up - 10 Aprile 2026\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - Fix\n\na\n\n---\n\n### Prossimi passi\n\nb\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.reader import lista_progetti

    _reset_config()
    result = lista_progetti(data_inizio="2026-04-09", data_fine="2026-04-09")

    nomi = [p["nome"] for p in result["progetti"]]
    assert nomi == ["SmarTicket"]  # "Prossimi passi" filtered out
    assert result["progetti"][0]["sistema"] == "Teseo"
    assert result["progetti"][0]["occorrenze"] == 1
    assert result["per_sistema"]["Teseo"] == 1
    assert "troncato" in result and "max_progetti" in result
```

Run: `uv run pytest tests/test_reader.py -k lista_progetti_two_level -v` → FAIL.

- [ ] **Step 2: riscrivere `lista_progetti`**

In `src/mcp_cronos/tools/reader.py`, aggiungere l'import:

```python
from mcp_cronos.utils.projects import system_of
```

Aggiungere il parametro `max_progetti: int = 100` alla firma di `lista_progetti` (dopo `ultimi_giorni`). Sostituire il blocco di raccolta e il `return` finale con un'aggregazione che traccia conteggi e prima/ultima data per progetto canonico:

```python
    progetti_count: dict[str, int] = {}
    progetti_date: dict[str, list[str]] = {}

    for d in dates_to_read:
        file_path = get_file_path(d)
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            for proj in extract_projects(content):
                progetti_count[proj] = progetti_count.get(proj, 0) + 1
                progetti_date.setdefault(proj, []).append(str(d))

    ordinati = sorted(progetti_count.items(), key=lambda kv: kv[1], reverse=True)
    troncato = len(ordinati) > max_progetti
    progetti = []
    per_sistema: dict[str, int] = {}
    for nome, occ in ordinati[:max_progetti]:
        date_list = sorted(progetti_date[nome])
        sistema = system_of(nome)
        progetti.append(
            {
                "nome": nome,
                "sistema": sistema,
                "occorrenze": occ,
                "prima_data": date_list[0],
                "ultima_data": date_list[-1],
            }
        )
        if sistema:
            per_sistema[sistema] = per_sistema.get(sistema, 0) + occ

    return {
        "periodo": {"da": str(start), "a": str(end), "giorni_analizzati": len(dates_to_read)},
        "totale_progetti": len(progetti_count),
        "max_progetti": max_progetti,
        "troncato": troncato,
        "per_sistema": per_sistema,
        "progetti": progetti,
    }
```

(Rimuovere il vecchio codice che costruiva `progetti_dettaglio` con la lista completa delle date.)

In `server.py`, nella `Tool(name="cronos_lista_progetti", ...)`, aggiungere `max_progetti` alle `properties` (intero, "Numero massimo di progetti restituiti (default 100)") e nel dispatch `max_progetti=arguments.get("max_progetti", 100)`.

- [ ] **Step 3: verificare**

Run: `uv run pytest tests/test_reader.py -v` → verde (aggiornare eventuali test esistenti di `lista_progetti` che si aspettavano il vecchio campo `date`/`progetti_dettaglio`: ora ogni progetto ha `prima_data`/`ultima_data`; non indebolire, adegua al nuovo contratto dichiarato in spec).
Run: `uv run pytest -q` → verde. `uv run ruff check src/mcp_cronos/tools/reader.py src/mcp_cronos/server.py tests/test_reader.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/tools/reader.py src/mcp_cronos/server.py tests/test_reader.py
git commit -m "feat(reader): two-level, capped lista_progetti

CHANGE: lista_progetti aggregates by canonical project, attaches the parent
system, rolls up per_sistema, returns prima_data/ultima_data instead of full
date lists, and caps output with max_progetti/troncato. Replaces the unbounded
raw-name listing."
```

---

## Task 5: tool `cronos_audit_progetti` (audit + bootstrap registro)

**Files:**
- Create: `src/mcp_cronos/tools/audit_progetti.py`
- Modify: `src/mcp_cronos/server.py`
- Test: `tests/test_audit_progetti.py` (nuovo)

**Interfaces:**
- Consumes: `_split_entries_respecting_fences` e `parse_diary_file` (markdown), `project_tokens`, `normalize_project`, `canonical_projects` (projects), `system_of`, date utils.
- Produces: funzione `audit_progetti(data_inizio=None, data_fine=None, ultimi_giorni=180, max_voci=200) -> dict` e tool `cronos_audit_progetti`.

- [ ] **Step 1: test che fallisce (nuovo file)**

Creare `tests/test_audit_progetti.py`:

```python
"""Tests for cronos_audit_progetti."""


def test_audit_clusters_and_drafts_registry(tmp_diario):
    month = tmp_diario / "2026" / "04"
    month.mkdir(parents=True, exist_ok=True)
    (month / "2026-04-09.md").write_text(
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### PayGW - a\n\nx\n\n---\n\n### PayGw - b\n\ny\n\n---\n\n"
        "### Prossimi passi\n\nz\n\n---\n\n## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )
    from mcp_cronos.tools.audit_progetti import audit_progetti

    result = audit_progetti(data_inizio="2026-04-09", data_fine="2026-04-09")

    # PayGW and PayGw cluster together by normalized key
    clusters = {c["chiave"]: c for c in result["cluster"]}
    assert "paygw" in clusters
    assert clusters["paygw"]["occorrenze"] == 2
    assert set(clusters["paygw"]["varianti"]) == {"PayGW", "PayGw"}
    # a ready-to-edit TOML draft is provided
    assert "[cronos.projects." in result["bozza_toml"]
    assert "totale_nomi_grezzi" in result
```

Run: `uv run pytest tests/test_audit_progetti.py -v` → FAIL.

- [ ] **Step 2: implementare il tool**

Creare `src/mcp_cronos/tools/audit_progetti.py`:

```python
"""Audit and bootstrap helper for the project registry.

Scans diary headings over a period, clusters the raw project tokens by their
normalized key, and emits a ready-to-edit [cronos.projects] draft so building
the registry is simple for any user. Read-only: it never writes cronos.toml.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.utils.dates import get_date_range, get_file_path, get_today, parse_date
from mcp_cronos.utils.markdown import _split_entries_respecting_fences
from mcp_cronos.utils.projects import normalize_project, project_tokens


def audit_progetti(
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 180,
    max_voci: int = 200,
) -> dict:
    """Cluster raw project tokens over a period and draft a registry block."""
    today = get_today()
    if data_inizio and data_fine:
        try:
            start = parse_date(data_inizio)
            end = parse_date(data_fine)
            if start > end:
                return {"errore": "data_inizio deve essere precedente a data_fine"}
        except ValueError as e:
            return {"errore": str(e)}
    else:
        start = today - timedelta(days=ultimi_giorni - 1)
        end = today

    # key -> {varianti: {display: count}, occorrenze: int}
    clusters: dict[str, dict] = {}
    for d in get_date_range(start, end):
        file_path = get_file_path(d)
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        for part in _split_entries_respecting_fences(content):
            first_line = part.split("\n", 1)[0]
            if not first_line.startswith("### "):
                continue
            header = first_line[4:].strip()
            for token in project_tokens(header):
                key = normalize_project(token)
                if not key:
                    continue
                c = clusters.setdefault(key, {"varianti": {}, "occorrenze": 0})
                c["varianti"][token] = c["varianti"].get(token, 0) + 1
                c["occorrenze"] += 1

    ordered = sorted(clusters.items(), key=lambda kv: kv[1]["occorrenze"], reverse=True)
    troncato = len(ordered) > max_voci
    ordered = ordered[:max_voci]

    cluster_out = []
    draft_lines: list[str] = []
    for key, data in ordered:
        varianti = sorted(data["varianti"], key=lambda v: data["varianti"][v], reverse=True)
        canonical = varianti[0]
        cluster_out.append(
            {
                "chiave": key,
                "canonico_proposto": canonical,
                "varianti": varianti,
                "occorrenze": data["occorrenze"],
            }
        )
        draft_lines.append(f"[cronos.projects.{canonical!r}]")
        extra = [v for v in varianti if v != canonical]
        if extra:
            alias_repr = ", ".join(repr(v) for v in extra)
            draft_lines.append(f"alias = [{alias_repr}]")
        draft_lines.append("")

    return {
        "periodo": {"da": str(start), "a": str(end)},
        "totale_nomi_grezzi": len(clusters),
        "max_voci": max_voci,
        "troncato": troncato,
        "cluster": cluster_out,
        "bozza_toml": "\n".join(draft_lines).strip(),
        "nota": (
            "Bozza pronta da incollare in cronos.toml. Rivedi i canonici, "
            "accorpa con 'alias' i sinonimi veri, e aggiungi 'sistema = \"...\"' "
            "dove vuoi la gerarchia. Il tool non scrive il file."
        ),
    }
```

In `server.py`: importare `from mcp_cronos.tools.audit_progetti import audit_progetti`, aggiungere la `Tool(name="cronos_audit_progetti", ...)` con descrizione (cosa fa + che restituisce una bozza di registro), `inputSchema` con `data_inizio`/`data_fine`/`ultimi_giorni`/`max_voci` opzionali, e il ramo dispatch `elif name == "cronos_audit_progetti": result = audit_progetti(data_inizio=arguments.get("data_inizio"), data_fine=arguments.get("data_fine"), ultimi_giorni=arguments.get("ultimi_giorni", 180), max_voci=arguments.get("max_voci", 200))`.

- [ ] **Step 3: verificare**

Run: `uv run pytest tests/test_audit_progetti.py -v` → PASS.
Run: `uv run pytest -q` → verde. `uv run ruff check src/mcp_cronos/tools/audit_progetti.py src/mcp_cronos/server.py tests/test_audit_progetti.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/tools/audit_progetti.py src/mcp_cronos/server.py tests/test_audit_progetti.py
git commit -m "feat(audit): add cronos_audit_progetti with registry bootstrap

CHANGE: New read-only tool that clusters raw project tokens over a period by
normalized key and emits a ready-to-edit [cronos.projects] draft, so building
the project list is simple for any user. Does not write cronos.toml."
```

---

## Task 6: Documentazione

**Files:**
- Modify: `README.md`, `CLAUDE.md`

- [ ] **Step 1: README — nuova sezione "Project registry (optional)" (entrambe le lingue)**

Aggiungere dopo la documentazione di `cronos.toml`, in entrambe le sezioni lingua, un blocco che spiega in modo CHIARO:
- il registro e' facoltativo; senza configurazione Cronos funziona out-of-the-box e nessun nome di progetto e' cablato nel pacchetto;
- il modello a due livelli con un esempio NEUTRO (non Teseo), es.:
```toml
[cronos.projects.api-gateway]
sistema = "Platform"
alias = ["APIGateway", "api gw"]

[cronos.projects.billing]
sistema = "Platform"
```
- come creare la lista in modo semplice: lanciare `cronos_audit_progetti`, copiare la `bozza_toml`, aggiungere `sistema` dove serve, salvare in `cronos.toml`.

Documentare anche i tre nuovi/aggiornati comportamenti dei tool: `cronos_lista_progetti` (output a due livelli con `per_sistema`, `prima_data`/`ultima_data`, `max_progetti`/`troncato`) e il nuovo `cronos_audit_progetti` (sezione tool dedicata in entrambe le lingue).

- [ ] **Step 2: CLAUDE.md**

Aggiungere `projects` e `audit_progetti` alla lista degli scope di commit; citare il modulo `utils/projects.py` e il tool `cronos_audit_progetti` nell'albero architettura e nel tool workflow; aggiornare il conteggio tool (15). Nota: il registro e' opzionale e generico.

- [ ] **Step 3: verifica conteggio e commit**

Run: `uv run python -c "from mcp_cronos.server import TOOLS; print(len(TOOLS))"` → atteso 15. Confermare che `cronos_audit_progetti` abbia una sezione `####` in entrambe le lingue del README.

```bash
git add README.md CLAUDE.md
git commit -m "docs: document optional project registry and audit tool

CHANGE: Adds a 'Project registry (optional)' README section (both languages) with
a neutral two-level example and the simple bootstrap flow via cronos_audit_progetti,
documents the new two-level lista_progetti output and the audit tool, and updates
CLAUDE.md (tool count, scopes, architecture)."
```

---

## Chiusura

- [ ] **Step finale: suite + lint**

Run: `uv run pytest -q` → tutti verdi.
Run: `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` → puliti.

Branch `feature/project-identity` pronto per il merge (decisione utente, mai push automatico).

## Passo post-implementazione (dato utente, NON nel repo)

Dopo il merge, lanciare `cronos_audit_progetti` sul diario reale dell'utente per
generare la `bozza_toml`, presentarla all'utente, applicare la tassonomia
verificata (Teseo coi suoi cinque componenti, Rapsodia, le linee separate, i
trasversali) come `sistema`/`alias`, e — con l'ok dell'utente — salvarla nel suo
`cronos.toml` (NON nel repository di mcp-cronos). Questo e' il seed del SUO
registro, dato utente, fuori dal pacchetto.

## Note di esecuzione
- Test-first ogni task. Ordine: 1 (config + normalize) -> 2 (risolutori) -> 3 (extract_projects) -> 4 (lista_progetti) -> 5 (audit) -> 6 (doc).
- Import cycle: `utils/projects.py` importa `load_config` solo lazy dentro le funzioni; `config.py` importa `normalize_project` a livello modulo. Se un test fallisce con ImportError, e' qui che guardare.
- Se un test esistente si rompe per il nuovo comportamento (em-dash, output `lista_progetti`), adeguarlo al contratto della spec senza indebolirlo; se il comportamento atteso e' ambiguo, fermarsi ed escalare.
