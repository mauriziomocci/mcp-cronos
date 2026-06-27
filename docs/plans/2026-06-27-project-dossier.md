# Project dossier (D1) — Piano di implementazione

> **Per worker agentici:** SUB-SKILL: superpowers:subagent-driven-development. Step a checkbox.

**Goal:** un tool `cronos_progetto` che ricostruisce la storia completa di un progetto o di un sistema dal diario: timeline cronologica, riferimenti aggregati, breakdown per componente (roll-up di sistema), bloccanti per giorno. Sola lettura, cappato.

**Architettura:** `members_of` in `utils/projects.py` risolve target -> insieme di canonici (sistema -> componenti+se'). Nuovo `tools/dossier.py` fa la propria segmentazione (`split_entries_respecting_fences`) e matcha via `canonical_projects`, indipendente da `parse_entries`. Tool registrato in `server.py`.

**Tech Stack:** Python 3.10+, pytest, ruff.

**Riferimento spec:** `docs/specs/2026-06-27-project-dossier-design.md`

## Global Constraints
- Inglese nel codice/commit; piano/spec in italiano. PEP8, 100 col, doppi apici, ruff pulito, zero test falliti.
- Non distruttivo, sola lettura del diario. Output cappato (stile fase B).
- `utils/projects.py` non importa `config` a livello modulo (load_config lazy nelle funzioni).

---

## Task 1: `members_of` in projects.py

**Files:**
- Modify: `src/mcp_cronos/utils/projects.py`
- Test: `tests/test_projects.py`

**Interfaces:**
- Consumes: `normalize_project`, `load_config()` (lazy) -> `project_canonical`, `project_system`.
- Produces: `members_of(target: str) -> set[str]`.

- [ ] **Step 1: test che fallisce**

Append a `tests/test_projects.py`:

```python
def test_members_of_system_rolls_up(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n'
        '[cronos.projects.Teseo]\nalias = ["Teseo Infra"]\n\n'
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Infomobile]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Goceano]\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.projects import members_of

    _reset_config()
    # system rolls up to its components + the system itself
    assert members_of("Teseo") == {"Teseo", "SmarTicket", "Infomobile"}
    # case/alias resolves then rolls up
    assert members_of("teseo infra") == {"Teseo", "SmarTicket", "Infomobile"}
    # a component -> just itself
    assert members_of("SmarTicket") == {"SmarTicket"}
    # a standalone -> just itself
    assert members_of("Goceano") == {"Goceano"}


def test_members_of_passthrough_without_registry(tmp_diario):
    from mcp_cronos.utils.projects import members_of

    assert members_of("Anything") == {"Anything"}
```

Run: `uv run pytest tests/test_projects.py -k members_of -v` → FAIL.

- [ ] **Step 2: implementare `members_of`**

In `src/mcp_cronos/utils/projects.py`, aggiungere:

```python
def members_of(target: str) -> set[str]:
    """Return the canonical project names a dossier on `target` should include.

    Resolves `target` to a canonical name via the registry (normalization +
    aliases). If that canonical is a system (appears as a parent in the
    registry), returns all its components plus the system name itself. Otherwise
    returns just the resolved canonical. With an empty registry it returns the
    target unchanged.
    """
    from mcp_cronos.config import load_config  # noqa: PLC0415 — lazy to avoid import cycle

    config = load_config()
    resolved = config.project_canonical.get(normalize_project(target), target)
    systems = set(config.project_system.values())
    if resolved in systems:
        members = {c for c, sistema in config.project_system.items() if sistema == resolved}
        members.add(resolved)
        return members
    return {resolved}
```

- [ ] **Step 3: verificare**

Run: `uv run pytest tests/test_projects.py -k members_of -v` → PASS.
Run: `uv run pytest -q` → verde. `uv run ruff check src/mcp_cronos/utils/projects.py tests/test_projects.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/utils/projects.py tests/test_projects.py
git commit -m "feat(projects): add members_of for dossier roll-up

CHANGE: members_of resolves a target to its canonical and, when that canonical
is a system, returns all its components plus the system itself; otherwise the
single canonical. Pass-through when no registry. Basis for the project dossier."
```

---

## Task 2: `tools/dossier.py`

**Files:**
- Create: `src/mcp_cronos/tools/dossier.py`
- Test: `tests/test_dossier.py` (nuovo)

**Interfaces:**
- Consumes: `members_of`, `canonical_projects`, `normalize_project` (projects); `split_entries_respecting_fences`, `extract_references`, `parse_diary_file` (markdown); `get_date_range`, `get_file_path`, `get_today`, `parse_date` (dates); `load_config` (config).
- Produces: `dossier_progetto(progetto, data_inizio=None, data_fine=None, ultimi_giorni=180, max_voci=50) -> dict`.

- [ ] **Step 1: test che fallisce (nuovo file)**

Creare `tests/test_dossier.py`:

```python
"""Tests for cronos_progetto (project dossier)."""


def _write_registry(diario):
    (diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n'
        '[cronos.projects.Teseo]\n\n'
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Infomobile]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Goceano]\n',
        encoding="utf-8",
    )


def _write_day(diario, ymd, body):
    y, m, _ = ymd.split("-")
    d = diario / y / m / ymd
    d.mkdir(parents=True, exist_ok=True)
    (d / "raw.md").write_text(body, encoding="utf-8")


def test_dossier_system_rolls_up_components(tmp_diario):
    _write_registry(tmp_diario)
    _write_day(
        tmp_diario, "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - Fix login\n\nFixed.\n\n**Riferimenti:**\n- Repository: st-backend\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    _write_day(
        tmp_diario, "2026-04-09",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### Infomobile — GTFS import\n\nImported.\n\n---\n\n"
        "### Goceano - other\n\nx\n\n---\n\n"
        "## Bloccanti\n\nAttesa credenziali vendor\n",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.dossier import dossier_progetto

    _reset_config()
    r = dossier_progetto("Teseo", data_inizio="2026-04-08", data_fine="2026-04-09")

    assert r["e_sistema"] is True
    assert set(r["membri"]) == {"Teseo", "SmarTicket", "Infomobile"}
    # Goceano is NOT part of Teseo -> excluded
    titoli = [v["titolo"] for v in r["timeline"]]
    assert any("SmarTicket" in t for t in titoli)
    assert any("Infomobile" in t for t in titoli)
    assert all("Goceano" not in t for t in titoli)
    assert r["num_voci"] == 2
    assert r["per_progetto"].get("SmarTicket") == 1
    assert r["per_progetto"].get("Infomobile") == 1
    # aggregated references
    assert "st-backend" in r["riferimenti"].get("repository", [])
    # day-level blocker captured on the day Infomobile (a member) appeared
    assert any(b["data"] == "2026-04-09" and "credenziali" in b["testo"] for b in r["bloccanti"])
    # timeline chronological
    assert r["timeline"] == sorted(r["timeline"], key=lambda v: v["data"])


def test_dossier_single_component(tmp_diario):
    _write_registry(tmp_diario)
    _write_day(
        tmp_diario, "2026-04-09",
        "# T\n\n## Cosa ho fatto ieri\n\n### SmarTicket - x\n\na\n\n---\n\n"
        "### Infomobile - y\n\nb\n\n---\n\n## Bloccanti\n\nNessuno\n",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.dossier import dossier_progetto

    _reset_config()
    r = dossier_progetto("SmarTicket", data_inizio="2026-04-09", data_fine="2026-04-09")
    assert r["e_sistema"] is False
    assert r["num_voci"] == 1
    assert [v["titolo"] for v in r["timeline"]] == ["SmarTicket - x"]


def test_dossier_truncates(tmp_diario):
    _write_registry(tmp_diario)
    body = "# T\n\n## Cosa ho fatto ieri\n\n"
    for i in range(5):
        body += f"### SmarTicket - task {i}\n\nwork {i}\n\n---\n\n"
    body += "## Bloccanti\n\nNessuno\n"
    _write_day(tmp_diario, "2026-04-09", body)
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.dossier import dossier_progetto

    _reset_config()
    r = dossier_progetto("SmarTicket", data_inizio="2026-04-09", data_fine="2026-04-09", max_voci=2)
    assert r["num_voci"] == 5
    assert len(r["timeline"]) == 2
    assert r["troncato"] is True
```

Run: `uv run pytest tests/test_dossier.py -v` → FAIL (module missing).

- [ ] **Step 2: creare `src/mcp_cronos/tools/dossier.py`**

```python
"""Project dossier: the full story of a project or system from the diary.

Read-only. Scans the diary over a period, matches entries to a target project
(or system, with component roll-up) using canonical identity, and assembles a
chronological timeline, aggregated references, a per-component breakdown, and
the day-level blockers seen on days the project was worked. Output is capped.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.config import load_config
from mcp_cronos.utils.dates import get_date_range, get_file_path, get_today, parse_date
from mcp_cronos.utils.markdown import (
    extract_references,
    parse_diary_file,
    split_entries_respecting_fences,
)
from mcp_cronos.utils.projects import canonical_projects, members_of, normalize_project

_DEFAULT_NO_BLOCKERS = {"nessuno", "none", ""}


def dossier_progetto(
    progetto: str,
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 180,
    max_voci: int = 50,
) -> dict:
    """Assemble the dossier for a project or system over a period."""
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

    config = load_config()
    resolved = config.project_canonical.get(normalize_project(progetto), progetto)
    e_sistema = resolved in set(config.project_system.values())
    target_set = members_of(progetto)

    timeline: list[dict] = []
    per_progetto: dict[str, int] = {}
    refs_acc: dict[str, set] = {}
    bloccanti: list[dict] = []
    giorni: set[str] = set()

    for d in get_date_range(start, end):
        file_path = get_file_path(d)
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        day_has_project = False
        for part in split_entries_respecting_fences(content):
            head_body = part.split("\n", 1)
            first = head_body[0]
            if not first.startswith("### "):
                continue
            heading = first[4:].strip()
            matched = [p for p in canonical_projects(heading) if p in target_set]
            if not matched:
                continue
            day_has_project = True
            body = head_body[1] if len(head_body) > 1 else ""
            timeline.append(
                {
                    "data": str(d),
                    "progetto": matched,
                    "titolo": heading,
                    "snippet": body.strip()[:200],
                }
            )
            for p in matched:
                per_progetto[p] = per_progetto.get(p, 0) + 1
            refs = extract_references(body)
            if refs:
                for k, v in refs.items():
                    refs_acc.setdefault(k, set()).add(v)
        if day_has_project:
            giorni.add(str(d))
            diary = parse_diary_file(file_path)
            if diary and diary.bloccanti.strip().lower() not in _DEFAULT_NO_BLOCKERS:
                bloccanti.append({"data": str(d), "testo": diary.bloccanti.strip()[:300]})

    timeline.sort(key=lambda v: v["data"])
    troncato = len(timeline) > max_voci
    timeline_out = timeline[-max_voci:] if troncato else timeline
    date_all = sorted(giorni)

    return {
        "progetto": progetto,
        "e_sistema": e_sistema,
        "membri": sorted(target_set) if e_sistema else None,
        "periodo": {"da": str(start), "a": str(end)},
        "num_voci": len(timeline),
        "num_giorni": len(giorni),
        "prima_data": date_all[0] if date_all else None,
        "ultima_data": date_all[-1] if date_all else None,
        "per_progetto": dict(sorted(per_progetto.items(), key=lambda kv: kv[1], reverse=True)),
        "timeline": timeline_out,
        "riferimenti": {k: sorted(v) for k, v in sorted(refs_acc.items())},
        "bloccanti": bloccanti,
        "max_voci": max_voci,
        "troncato": troncato,
    }
```

- [ ] **Step 3: verificare**

Run: `uv run pytest tests/test_dossier.py -v` → PASS.
Run: `uv run pytest -q` → verde. `uv run ruff check src/mcp_cronos/tools/dossier.py tests/test_dossier.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/tools/dossier.py tests/test_dossier.py
git commit -m "feat(dossier): add project/system dossier assembly

CHANGE: dossier_progetto scans the diary, matches entries to a project or
system (component roll-up) via canonical identity, and returns a chronological
timeline, aggregated references, per-component counts and day-level blockers,
capped by max_voci. Independent of parse_entries."
```

---

## Task 3: registrare il tool `cronos_progetto`

**Files:**
- Modify: `src/mcp_cronos/server.py`
- Test: `tests/test_dossier.py`

- [ ] **Step 1: test dispatch**

Append a `tests/test_dossier.py`:

```python
def test_cronos_progetto_tool_registered():
    from mcp_cronos.server import TOOLS

    assert any(t.name == "cronos_progetto" for t in TOOLS)
```

Run: `uv run pytest tests/test_dossier.py -k tool_registered -v` → FAIL.

- [ ] **Step 2: registrare in server.py**

Import: `from mcp_cronos.tools.dossier import dossier_progetto`.
Aggiungere alla lista `TOOLS` una `Tool(name="cronos_progetto", ...)` seguendo lo stile esatto degli altri tool: description che spiega che ricostruisce la storia completa di un progetto o sistema (con roll-up dei componenti), elenca i parametri, e `inputSchema` con `progetto` (string, required), `data_inizio`/`data_fine` (string opzionali), `ultimi_giorni` (integer, default 180), `max_voci` (integer, default 50). Esempio neutro nella descrizione (NON Teseo): es. `"Backend API"`.
Aggiungere il ramo dispatch in `call_tool`:
```python
        elif name == "cronos_progetto":
            result = dossier_progetto(
                progetto=arguments["progetto"],
                data_inizio=arguments.get("data_inizio"),
                data_fine=arguments.get("data_fine"),
                ultimi_giorni=arguments.get("ultimi_giorni", 180),
                max_voci=arguments.get("max_voci", 50),
            )
```

- [ ] **Step 3: verificare**

Run: `uv run pytest tests/test_dossier.py -v` → verde.
Run: `uv run python -c "from mcp_cronos.server import TOOLS; print(len(TOOLS))"` → 16.
Run: `uv run pytest -q` → verde. `uv run ruff check src/mcp_cronos/server.py tests/test_dossier.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/server.py tests/test_dossier.py
git commit -m "feat(server): register cronos_progetto dossier tool

CHANGE: Registers cronos_progetto in TOOLS and dispatch, exposing
dossier_progetto. Brings the tool count to 16."
```

---

## Task 4: documentazione

**Files:**
- Modify: `README.md`, `CLAUDE.md`

- [ ] **Step 1: README (entrambe le lingue)**

Aggiungere una sezione tool `#### cronos_progetto` in inglese e in italiano: cosa fa (storia completa di un progetto o sistema, timeline, riferimenti aggregati, breakdown per componente sul roll-up di sistema, bloccanti per giorno), i parametri (`progetto` obbligatorio; `data_inizio`/`data_fine`/`ultimi_giorni`/`max_voci` opzionali), e la forma del risultato (timeline cappata, riferimenti, per_progetto, bloccanti). Esempio NEUTRO (no Teseo). Usare la descrizione/inputSchema in `server.py` come fonte.

- [ ] **Step 2: CLAUDE.md**

Aggiornare il conteggio tool a 16 (cercare "15 tool"/"(15 ...)"); aggiungere `tools/dossier.py` all'albero architettura; aggiungere `dossier` alla lista degli scope di commit; una riga nel tool workflow sul dossier per progetto.

- [ ] **Step 3: verifica e commit**

Run: `uv run python -c "from mcp_cronos.server import TOOLS; print(len(TOOLS))"` → 16; confermare `#### cronos_progetto` x2 nel README.

```bash
git add README.md CLAUDE.md
git commit -m "docs: document cronos_progetto dossier tool

CHANGE: Documents cronos_progetto in README (both languages, neutral example)
and updates CLAUDE.md (tool count 16, dossier scope, architecture)."
```

---

## Chiusura
- [ ] **Suite + lint:** `uv run pytest -q` verde; `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` puliti.
- [ ] **Verifica sul campo (repo, diario reale):**
  `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/Users/mauriziomocci/Documents/workspace/Diario uv run python -c "from mcp_cronos.tools.dossier import dossier_progetto; import json; r=dossier_progetto('Teseo', ultimi_giorni=180, max_voci=15); print('e_sistema', r['e_sistema'], 'membri', r['membri']); print('num_voci', r['num_voci'], 'num_giorni', r['num_giorni']); print('per_progetto', r['per_progetto']); print('riferimenti keys', list(r['riferimenti'].keys()))"`
  Confermare che il roll-up di Teseo raccolga i componenti e produca una storia sensata; ripetere per "SmarTicket".

Branch `feature/project-dossier` pronto per il merge (decisione utente, mai push automatico).

## Note di esecuzione
- Test-first ogni task. Ordine: 1 (members_of) -> 2 (dossier) -> 3 (server) -> 4 (doc).
- Nessun import cycle: `dossier.py` e' un modulo foglia (solo server lo importa); importa markdown/projects/dates/config a livello modulo (projects fa load_config lazy).
- Se un test esistente si rompe, adeguarlo al comportamento corretto senza indebolirlo; se ambiguo, fermarsi ed escalare.
