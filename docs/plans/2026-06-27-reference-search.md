# Cross-reference search (D3) — Piano di implementazione

> **Per worker agentici:** SUB-SKILL: superpowers:subagent-driven-development. Step a checkbox.

**Goal:** un tool `cronos_riferimento` che ricostruisce il filo di un riferimento (ticket/MR/repo) nel diario: timeline project-aware delle voci che lo menzionano, piu' i progetti e sistemi coinvolti.

**Architettura:** nuovo `tools/riferimento.py` con segmentazione propria (`split_entries_respecting_fences` + `canonical_projects`), match a sottostringa case-insensitive. Tool registrato in server.py.

**Tech Stack:** Python 3.10+, pytest, ruff.

**Riferimento spec:** `docs/specs/2026-06-27-reference-search-design.md`

## Global Constraints
- Inglese nel codice/commit; piano/spec in italiano. PEP8, 100 col, doppi apici, ruff pulito, zero test falliti.
- Sola lettura, non distruttivo, output cappato.
- **Documentazione obbligatoria nello stesso slice**: README EN+IT, CLAUDE.md, e CHANGELOG.md `[Unreleased]` (regole fisse dell'utente).

---

## Task 1: `tools/riferimento.py`

**Files:**
- Create: `src/mcp_cronos/tools/riferimento.py`
- Test: `tests/test_riferimento.py` (nuovo)

**Interfaces:**
- Consumes: `canonical_projects`, `system_of` (projects); `split_entries_respecting_fences` (markdown); `get_date_range`, `get_file_path`, `get_today`, `parse_date` (dates).
- Produces: `traccia_riferimento(riferimento, data_inizio=None, data_fine=None, ultimi_giorni=180, max_voci=50) -> dict`.

- [ ] **Step 1: test che fallisce (nuovo file)**

Creare `tests/test_riferimento.py`:

```python
"""Tests for cronos_riferimento."""


def _reg(diario):
    (diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n'
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Infomobile]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Goceano]\n',
        encoding="utf-8",
    )


def _day(diario, ymd, body):
    y, m, _ = ymd.split("-")
    p = diario / y / m / ymd
    p.mkdir(parents=True, exist_ok=True)
    (p / "raw.md").write_text(body, encoding="utf-8")


def test_riferimento_traces_ticket_across_projects(tmp_diario):
    _reg(tmp_diario)
    _day(
        tmp_diario, "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - export\n\nlavoro su DVT-552 export.\n\n---\n\n"
        "### Goceano - altro\n\nniente di rilevante.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    _day(
        tmp_diario, "2026-04-10",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### Infomobile - fix collegato\n\nfix per dvt-552 lato infomobile.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.riferimento import traccia_riferimento

    _reset_config()
    r = traccia_riferimento("DVT-552", data_inizio="2026-04-01", data_fine="2026-04-30")

    assert r["num_voci"] == 2          # SmarTicket entry + Infomobile entry (case-insensitive)
    assert r["num_giorni"] == 2
    assert r["progetti"] == ["Infomobile", "SmarTicket"]
    assert r["sistemi"] == ["Teseo"]
    titoli = [v["titolo"] for v in r["timeline"]]
    assert "SmarTicket - export" in titoli
    assert "Infomobile - fix collegato" in titoli
    assert all("Goceano" not in t for t in titoli)   # Goceano entry has no DVT-552
    assert r["timeline"] == sorted(r["timeline"], key=lambda v: v["data"])


def test_riferimento_empty_when_absent(tmp_diario):
    _reg(tmp_diario)
    _day(
        tmp_diario, "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n### SmarTicket - x\n\nniente.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.riferimento import traccia_riferimento

    _reset_config()
    r = traccia_riferimento("NOPE-999", data_inizio="2026-04-01", data_fine="2026-04-30")
    assert r["num_voci"] == 0
    assert r["progetti"] == []
    assert r["sistemi"] == []
    assert r["timeline"] == []
    assert r["troncato"] is False


def test_riferimento_truncates(tmp_diario):
    _reg(tmp_diario)
    body = "# T\n\n## Cosa ho fatto ieri\n\n"
    for i in range(4):
        body += f"### SmarTicket - task {i}\n\ntocca DVT-1 qui.\n\n---\n\n"
    body += "## Bloccanti\n\nNessuno\n"
    _day(tmp_diario, "2026-04-08", body)
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.riferimento import traccia_riferimento

    _reset_config()
    r = traccia_riferimento("DVT-1", data_inizio="2026-04-01", data_fine="2026-04-30", max_voci=2)
    assert r["num_voci"] == 4
    assert len(r["timeline"]) == 2
    assert r["troncato"] is True
```
Run `uv run pytest tests/test_riferimento.py -v` → FAIL (module missing).

- [ ] **Step 2: creare src/mcp_cronos/tools/riferimento.py**

```python
"""Cross-reference search: the thread of a ticket / MR / repo across the diary.

Read-only. Scans the diary over a period and returns every entry that mentions a
given reference (case-insensitive substring), tagged with its canonical project,
plus the projects and systems the reference spans. Capped output.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.utils.dates import get_date_range, get_file_path, get_today, parse_date
from mcp_cronos.utils.markdown import split_entries_respecting_fences
from mcp_cronos.utils.projects import canonical_projects, system_of


def traccia_riferimento(
    riferimento: str,
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 180,
    max_voci: int = 50,
) -> dict:
    """Trace every diary entry that mentions a reference, project-aware."""
    if not riferimento or not riferimento.strip():
        return {"errore": "riferimento vuoto"}
    needle = riferimento.strip().lower()

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

    timeline: list[dict] = []
    progetti: set[str] = set()
    giorni: set[str] = set()

    for d in get_date_range(start, end):
        file_path = get_file_path(d)
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        for part in split_entries_respecting_fences(content):
            if needle not in part.lower():
                continue
            head_body = part.split("\n", 1)
            first = head_body[0]
            if not first.startswith("### "):
                continue
            heading = first[4:].strip()
            projs = canonical_projects(heading)
            body = head_body[1] if len(head_body) > 1 else ""
            timeline.append(
                {
                    "data": str(d),
                    "progetto": projs,
                    "titolo": heading,
                    "snippet": body.strip()[:200],
                }
            )
            progetti.update(projs)
            giorni.add(str(d))

    timeline.sort(key=lambda v: v["data"])
    max_voci = max(0, max_voci)
    troncato = len(timeline) > max_voci
    timeline_out = timeline[len(timeline) - max_voci:] if troncato else timeline
    sistemi = sorted({s for p in progetti if (s := system_of(p))})
    date_all = sorted(giorni)

    return {
        "riferimento": riferimento,
        "periodo": {"da": str(start), "a": str(end)},
        "num_voci": len(timeline),
        "num_giorni": len(giorni),
        "prima_data": date_all[0] if date_all else None,
        "ultima_data": date_all[-1] if date_all else None,
        "progetti": sorted(progetti),
        "sistemi": sistemi,
        "timeline": timeline_out,
        "max_voci": max_voci,
        "troncato": troncato,
    }
```

- [ ] **Step 3: verificare**

Run: `uv run pytest tests/test_riferimento.py -v` → PASS.
Run: `uv run pytest -q` → verde. `uv run ruff check src/mcp_cronos/tools/riferimento.py tests/test_riferimento.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/tools/riferimento.py tests/test_riferimento.py
git commit -m "feat(riferimento): add cross-reference search

CHANGE: traccia_riferimento returns the project-aware timeline of every diary
entry mentioning a reference (ticket/MR/repo, case-insensitive), plus the
projects and systems it spans. Read-only, capped, own canonical segmentation."
```

---

## Task 2: registrare `cronos_riferimento`

**Files:**
- Modify: `src/mcp_cronos/server.py`
- Test: `tests/test_riferimento.py`

- [ ] **Step 1: test dispatch**

Append a `tests/test_riferimento.py`:
```python
def test_cronos_riferimento_tool_registered():
    from mcp_cronos.server import TOOLS

    assert any(t.name == "cronos_riferimento" for t in TOOLS)
```
Run `uv run pytest tests/test_riferimento.py -k tool_registered -v` → FAIL.

- [ ] **Step 2: registrare in server.py**

Import: `from mcp_cronos.tools.riferimento import traccia_riferimento`.
Aggiungere a `TOOLS` una `Tool(name="cronos_riferimento", ...)` nello stile esatto degli altri: description (italiano) — ricostruisce il filo di un riferimento (ticket, MR, repo) nel diario: ogni voce che lo menziona, in ordine, col progetto canonico, piu' i progetti e sistemi coinvolti. Usare quando l'utente chiede "tutto cio' che tocca <ticket>", "il filo della MR <n>", "dove ho lavorato sul repo X". Esempio NEUTRO. `inputSchema`: `riferimento` (string, required), `data_inizio`/`data_fine` (string opzionali), `ultimi_giorni` (int, default 180), `max_voci` (int, default 50). `required: ["riferimento"]`.
Dispatch:
```python
        elif name == "cronos_riferimento":
            result = traccia_riferimento(
                riferimento=arguments["riferimento"],
                data_inizio=arguments.get("data_inizio"),
                data_fine=arguments.get("data_fine"),
                ultimi_giorni=arguments.get("ultimi_giorni", 180),
                max_voci=arguments.get("max_voci", 50),
            )
```

- [ ] **Step 3: verificare**

Run: `uv run pytest tests/test_riferimento.py -v` → verde.
Run: `uv run python -c "from mcp_cronos.server import TOOLS; print(len(TOOLS))"` → 18.
Run: `uv run pytest -q` → verde. `uv run ruff check src/mcp_cronos/server.py tests/test_riferimento.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/server.py tests/test_riferimento.py
git commit -m "feat(server): register cronos_riferimento tool

CHANGE: Registers cronos_riferimento in TOOLS and dispatch. Tool count 18."
```

---

## Task 3: documentazione (README EN+IT + CLAUDE.md + CHANGELOG)

**Files:**
- Modify: `README.md`, `CLAUDE.md`, `CHANGELOG.md`

- [ ] **Step 1: README (ENTRAMBE le lingue)**

Aggiungere una sezione `#### cronos_riferimento` in inglese e in italiano: cosa fa (filo di un riferimento ticket/MR/repo nel diario, timeline project-aware, progetti e sistemi coinvolti), parametri (`riferimento` obbligatorio; `data_inizio`/`data_fine`/`ultimi_giorni` default 180/`max_voci` default 50 opzionali), forma del risultato (timeline cappata, progetti, sistemi, prima/ultima_data, troncato). Esempio NEUTRO (no Teseo). Fonte: description/inputSchema in server.py.

- [ ] **Step 2: CLAUDE.md**

Conteggio tool 17 -> 18 (cercare "17 tool"); aggiungere `tools/riferimento.py` all'albero; `riferimento` agli scope di commit; una riga nel tool workflow.

- [ ] **Step 3: CHANGELOG.md**

Sotto `## [Unreleased]`, in una sottosezione `### Added`, aggiungere:
```
- `cronos_riferimento`: project-aware cross-reference search — the timeline of
  every diary entry mentioning a given ticket/MR/repo, with the projects and
  systems it spans.
```
(Se `[Unreleased]` non ha ancora una sottosezione `### Added`, crearla.)

- [ ] **Step 4: verifica e commit**

Run: `uv run python -c "from mcp_cronos.server import TOOLS; print(len(TOOLS))"` → 18; `grep -c "cronos_riferimento" README.md` >= 2; `grep -n "18 tool" CLAUDE.md` presente; `grep -n "cronos_riferimento" CHANGELOG.md` presente.

```bash
git add README.md CLAUDE.md CHANGELOG.md
git commit -m "docs: document cronos_riferimento tool

CHANGE: Documents cronos_riferimento in README (both languages, neutral example),
updates CLAUDE.md (tool count 18, riferimento scope, architecture), and adds a
CHANGELOG [Unreleased] entry."
```

---

## Chiusura
- [ ] **Suite + lint:** `uv run pytest -q` verde; `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` puliti.
- [ ] **Verifica sul campo (repo, diario reale):**
  `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/Users/mauriziomocci/Documents/workspace/Diario uv run python -c "from mcp_cronos.tools.riferimento import traccia_riferimento; import json; r=traccia_riferimento('DVT-552', ultimi_giorni=180); print('num_voci', r['num_voci'], 'giorni', r['num_giorni']); print('progetti', r['progetti'], 'sistemi', r['sistemi']); print('timeline (prime 3):'); [print('  ', v['data'], v['titolo'][:50]) for v in r['timeline'][:3]]"`
  (Provare con un codice ticket reale presente nel diario; se DVT-552 non c'e', usarne uno noto.)

Branch `feature/reference-search` pronto per il merge (decisione utente, mai push automatico).

## Note di esecuzione
- Test-first. Ordine: 1 (riferimento) -> 2 (server) -> 3 (doc).
- `tools/riferimento.py` e' modulo foglia: importa markdown/projects/dates a livello modulo (projects fa load_config lazy), nessun ciclo.
