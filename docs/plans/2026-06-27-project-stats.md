# Project statistics (D2) — Piano di implementazione

> **Per worker agentici:** SUB-SKILL: superpowers:subagent-driven-development. Step a checkbox.

**Goal:** un tool `cronos_statistiche` che mostra la distribuzione del lavoro per progetto e per sistema in un periodo (voci + giorni distinti), il roll-up per sistema con quota %, e il trend per mese.

**Architettura:** nuovo `tools/statistiche.py` che fa la propria segmentazione canonica (come dossier/lista), aggrega voci/giorni/mese, fa roll-up via `system_of`. Tool registrato in server.py.

**Tech Stack:** Python 3.10+, pytest, ruff.

**Riferimento spec:** `docs/specs/2026-06-27-project-stats-design.md`

## Global Constraints
- Inglese nel codice/commit; piano/spec in italiano. PEP8, 100 col, doppi apici, ruff pulito, zero test falliti.
- Sola lettura, non distruttivo, output cappato.
- **Documentazione obbligatoria nello stesso slice**: README EN+IT + CLAUDE.md (regola fissa dell'utente).

---

## Task 1: `tools/statistiche.py`

**Files:**
- Create: `src/mcp_cronos/tools/statistiche.py`
- Test: `tests/test_statistiche.py` (nuovo)

**Interfaces:**
- Consumes: `canonical_projects`, `system_of` (projects); `split_entries_respecting_fences` (markdown); `get_date_range`, `get_file_path`, `get_today`, `parse_date` (dates).
- Produces: `statistiche(data_inizio=None, data_fine=None, ultimi_giorni=90, max_progetti=50) -> dict`.

- [ ] **Step 1: test che fallisce (nuovo file)**

Creare `tests/test_statistiche.py`:

```python
"""Tests for cronos_statistiche."""


def _reg(diario):
    (diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n'
        '[cronos.projects.Teseo]\n\n'
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Infomobile]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Goceano]\n',
        encoding="utf-8",
    )


def _day(diario, ymd, *headings):
    y, m, _ = ymd.split("-")
    p = diario / y / m / ymd
    p.mkdir(parents=True, exist_ok=True)
    body = "# T\n\n## Cosa ho fatto ieri\n\n"
    for h in headings:
        body += f"### {h}\n\nx\n\n---\n\n"
    body += "## Bloccanti\n\nNessuno\n"
    (p / "raw.md").write_text(body, encoding="utf-8")


def test_statistiche_distribution_and_rollup(tmp_diario):
    _reg(tmp_diario)
    _day(tmp_diario, "2026-04-08", "SmarTicket - a", "SmarTicket - b", "Goceano - c")
    _day(tmp_diario, "2026-05-09", "SmarTicket - d", "Infomobile - e")
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.statistiche import statistiche

    _reset_config()
    r = statistiche(data_inizio="2026-04-01", data_fine="2026-05-31")

    # totals: 5 entries, 2 active days, 3 projects, 1 system
    assert r["totali"]["voci"] == 5
    assert r["totali"]["giorni_attivi"] == 2
    assert r["totali"]["progetti"] == 3
    assert r["totali"]["sistemi"] == 1
    # per project (SmarTicket 3, Goceano 1, Infomobile 1)
    pp = {p["nome"]: p for p in r["per_progetto"]}
    assert pp["SmarTicket"]["voci"] == 3
    assert pp["SmarTicket"]["giorni"] == 2
    assert pp["SmarTicket"]["sistema"] == "Teseo"
    assert pp["Goceano"]["sistema"] is None
    # per system rollup: Teseo = SmarTicket(3) + Infomobile(1) = 4 entries
    ps = {s["sistema"]: s for s in r["per_sistema"]}
    assert ps["Teseo"]["voci"] == 4
    assert ps["Teseo"]["quota_pct"] == 80.0  # 4/5
    # temporal trend
    assert r["per_mese"] == {"2026-04": 3, "2026-05": 2}


def test_statistiche_empty_period_no_crash(tmp_diario):
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.statistiche import statistiche

    _reset_config()
    r = statistiche(data_inizio="2026-04-01", data_fine="2026-04-02")
    assert r["totali"]["voci"] == 0
    assert r["per_sistema"] == []
    assert r["per_progetto"] == []
    assert r["per_mese"] == {}
    assert r["troncato"] is False


def test_statistiche_truncates(tmp_diario):
    _reg(tmp_diario)
    _day(tmp_diario, "2026-04-08", "SmarTicket - a", "Infomobile - b", "Goceano - c")
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.statistiche import statistiche

    _reset_config()
    r = statistiche(data_inizio="2026-04-01", data_fine="2026-04-30", max_progetti=2)
    assert r["totali"]["progetti"] == 3
    assert len(r["per_progetto"]) == 2
    assert r["troncato"] is True
```
Run `uv run pytest tests/test_statistiche.py -v` → FAIL (module missing).

- [ ] **Step 2: creare src/mcp_cronos/tools/statistiche.py**

```python
"""Work statistics over the diary: distribution by project and system.

Read-only. Counts entries (each H3 heading resolving to a canonical project)
and distinct days per project over a period, rolls up to systems with a share
percentage, and reports a per-month activity trend. Effort is a proxy (entries
and days), not manual time-tracking.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.utils.dates import get_date_range, get_file_path, get_today, parse_date
from mcp_cronos.utils.markdown import split_entries_respecting_fences
from mcp_cronos.utils.projects import canonical_projects, system_of


def statistiche(
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 90,
    max_progetti: int = 50,
) -> dict:
    """Aggregate work statistics by project and system over a period."""
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

    voci: dict[str, int] = {}
    giorni: dict[str, set] = {}
    per_mese: dict[str, int] = {}
    giorni_attivi: set = set()

    for d in get_date_range(start, end):
        file_path = get_file_path(d)
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        mese = str(d)[:7]
        for part in split_entries_respecting_fences(content):
            first = part.split("\n", 1)[0]
            if not first.startswith("### "):
                continue
            projects = canonical_projects(first[4:].strip())
            if not projects:
                continue
            giorni_attivi.add(str(d))
            per_mese[mese] = per_mese.get(mese, 0) + 1
            for p in projects:
                voci[p] = voci.get(p, 0) + 1
                giorni.setdefault(p, set()).add(str(d))

    totale_voci = sum(voci.values())

    sys_voci: dict[str, int] = {}
    sys_giorni: dict[str, set] = {}
    for p, n in voci.items():
        s = system_of(p)
        if s:
            sys_voci[s] = sys_voci.get(s, 0) + n
            sys_giorni.setdefault(s, set()).update(giorni[p])

    per_sistema = [
        {
            "sistema": s,
            "voci": n,
            "giorni": len(sys_giorni[s]),
            "quota_pct": round(n / totale_voci * 100, 1) if totale_voci else 0.0,
        }
        for s, n in sorted(sys_voci.items(), key=lambda kv: kv[1], reverse=True)
    ]

    ordinati = sorted(voci.items(), key=lambda kv: kv[1], reverse=True)
    troncato = len(ordinati) > max_progetti
    per_progetto = [
        {"nome": p, "sistema": system_of(p), "voci": n, "giorni": len(giorni[p])}
        for p, n in ordinati[:max_progetti]
    ]

    return {
        "periodo": {"da": str(start), "a": str(end), "giorni_analizzati": (end - start).days + 1},
        "totali": {
            "voci": totale_voci,
            "giorni_attivi": len(giorni_attivi),
            "progetti": len(voci),
            "sistemi": len(sys_voci),
        },
        "per_sistema": per_sistema,
        "per_progetto": per_progetto,
        "per_mese": dict(sorted(per_mese.items())),
        "max_progetti": max_progetti,
        "troncato": troncato,
    }
```

- [ ] **Step 3: verificare**

Run: `uv run pytest tests/test_statistiche.py -v` → PASS.
Run: `uv run pytest -q` → verde. `uv run ruff check src/mcp_cronos/tools/statistiche.py tests/test_statistiche.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/tools/statistiche.py tests/test_statistiche.py
git commit -m "feat(statistiche): add work statistics by project and system

CHANGE: statistiche aggregates entries and distinct days per canonical project
over a period, rolls up to systems with a share percentage, and reports a
per-month activity trend. Read-only, capped, proxy effort. Own canonical
segmentation."
```

---

## Task 2: registrare `cronos_statistiche`

**Files:**
- Modify: `src/mcp_cronos/server.py`
- Test: `tests/test_statistiche.py`

- [ ] **Step 1: test dispatch**

Append a `tests/test_statistiche.py`:
```python
def test_cronos_statistiche_tool_registered():
    from mcp_cronos.server import TOOLS

    assert any(t.name == "cronos_statistiche" for t in TOOLS)
```
Run `uv run pytest tests/test_statistiche.py -k tool_registered -v` → FAIL.

- [ ] **Step 2: registrare in server.py**

Import: `from mcp_cronos.tools.statistiche import statistiche`.
Aggiungere a `TOOLS` una `Tool(name="cronos_statistiche", ...)` nello stile esatto degli altri: description (italiano) che spiega che mostra la distribuzione del lavoro per progetto e per sistema in un periodo (voci + giorni), il roll-up per sistema con quota %, e il trend per mese; quando usarlo ("dove e' andato il mese?", "quanto X vs Y?", "statistiche"); esempio NEUTRO. `inputSchema` con `data_inizio`/`data_fine` (string opzionali), `ultimi_giorni` (integer, default 90), `max_progetti` (integer, default 50), nessun required.
Dispatch:
```python
        elif name == "cronos_statistiche":
            result = statistiche(
                data_inizio=arguments.get("data_inizio"),
                data_fine=arguments.get("data_fine"),
                ultimi_giorni=arguments.get("ultimi_giorni", 90),
                max_progetti=arguments.get("max_progetti", 50),
            )
```

- [ ] **Step 3: verificare**

Run: `uv run pytest tests/test_statistiche.py -v` → verde.
Run: `uv run python -c "from mcp_cronos.server import TOOLS; print(len(TOOLS))"` → 17.
Run: `uv run pytest -q` → verde. `uv run ruff check src/mcp_cronos/server.py tests/test_statistiche.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/server.py tests/test_statistiche.py
git commit -m "feat(server): register cronos_statistiche tool

CHANGE: Registers cronos_statistiche in TOOLS and dispatch. Tool count 17."
```

---

## Task 3: documentazione (README EN+IT + CLAUDE.md)

**Files:**
- Modify: `README.md`, `CLAUDE.md`

- [ ] **Step 1: README (ENTRAMBE le lingue)**

Aggiungere una sezione `#### cronos_statistiche` in inglese e in italiano: cosa fa (distribuzione del lavoro per progetto e sistema, voci+giorni, quota % per sistema, trend per mese), i parametri (`data_inizio`/`data_fine`/`ultimi_giorni` default 90/`max_progetti` default 50, tutti opzionali), e la forma del risultato (totali, per_sistema, per_progetto, per_mese, troncato). Esempio NEUTRO (no Teseo). Usare description/inputSchema in `server.py` come fonte.

- [ ] **Step 2: CLAUDE.md**

Aggiornare conteggio tool 16 -> 17 (cercare "16 tool"/"(16 ...)"); aggiungere `tools/statistiche.py` all'albero architettura; aggiungere `statistiche` agli scope di commit; una riga nel tool workflow.

- [ ] **Step 3: verifica e commit**

Run: `uv run python -c "from mcp_cronos.server import TOOLS; print(len(TOOLS))"` → 17; `grep -c "cronos_statistiche" README.md` >= 2; `grep -n "17 tool" CLAUDE.md` presente.

```bash
git add README.md CLAUDE.md
git commit -m "docs: document cronos_statistiche tool

CHANGE: Documents cronos_statistiche in README (both languages, neutral example)
and updates CLAUDE.md (tool count 17, statistiche scope, architecture)."
```

---

## Chiusura
- [ ] **Suite + lint:** `uv run pytest -q` verde; `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` puliti.
- [ ] **Verifica sul campo (repo, diario reale):**
  `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/Users/mauriziomocci/Documents/workspace/Diario uv run python -c "from mcp_cronos.tools.statistiche import statistiche; import json; r=statistiche(ultimi_giorni=180); print('totali', r['totali']); print('per_sistema', json.dumps(r['per_sistema'], ensure_ascii=False)); print('per_mese', r['per_mese'])"`
  Confermare distribuzione Teseo/Rapsodia/altri e trend mensile sensati.

Branch `feature/project-stats` pronto per il merge (decisione utente, mai push automatico).

## Note di esecuzione
- Test-first. Ordine: 1 (statistiche) -> 2 (server) -> 3 (doc).
- `tools/statistiche.py` e' modulo foglia: importa markdown/projects/dates a livello modulo (projects fa load_config lazy), nessun ciclo.
