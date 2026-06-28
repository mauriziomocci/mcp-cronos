# Shared diary scanner refactor — Piano di implementazione

> **Per worker agentici:** SUB-SKILL: superpowers:subagent-driven-development. Step a checkbox.

**Goal:** rimuovere la duplicazione del ciclo di scansione giorno-per-giorno ripetuto da 5 tool (lista_progetti, dossier, statistiche, audit_progetti, riferimento), estraendo un generatore condiviso. Refactor PURO: comportamento identico, nessuna modifica ai test esistenti (304 verdi come rete di sicurezza).

**Architettura:** nuovo `utils/scan.py` con `iter_diary_days(start, end)` che per ogni giorno con file restituisce `(data, contenuto, entries)`, dove `entries` e' la lista di `(intestazione, corpo)` delle voci `### ` (fence-aware). I tool sostituiscono il loop inline con questo generatore. `extract_projects` resta invariato (funzione condivisa per i progetti di un contenuto).

**Tech Stack:** Python 3.10+, pytest, ruff.

## Global Constraints
- Inglese nel codice/commit; piano in italiano. PEP8, 100 col, doppi apici, ruff pulito.
- **Refactor a comportamento identico**: NESSUN test esistente va modificato; tutti e 304 devono restare verdi. Se un test cambia comportamento, e' un errore di migrazione — fermarsi.
- Nessun ciclo di import: `scan.py` importa `dates` e `markdown`; niente importa `scan` se non i tool. (`markdown`/`dates` non importano `scan`.)

---

## Task 1: `utils/scan.py` — `iter_diary_days`

**Files:**
- Create: `src/mcp_cronos/utils/scan.py`
- Test: `tests/test_scan.py` (nuovo)

**Interfaces:**
- Consumes: `get_date_range`, `get_file_path` (dates); `split_entries_respecting_fences` (markdown).
- Produces: `iter_diary_days(start: date, end: date) -> Iterator[tuple[date, str, list[tuple[str, str]]]]`.

- [ ] **Step 1: test che fallisce (nuovo file)**

Creare `tests/test_scan.py`:

```python
"""Tests for the shared diary scanner."""

from datetime import date


def _day(diario, ymd, body):
    y, m, _ = ymd.split("-")
    p = diario / y / m / ymd
    p.mkdir(parents=True, exist_ok=True)
    (p / "raw.md").write_text(body, encoding="utf-8")


def test_iter_diary_days_yields_entries_and_skips_missing(tmp_diario):
    _day(
        tmp_diario, "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - a\n\nbody A\n\n---\n\n"
        "### Infomobile - b\n\nbody B\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    # 2026-04-09 has no file -> skipped
    from mcp_cronos.utils.scan import iter_diary_days

    days = list(iter_diary_days(date(2026, 4, 8), date(2026, 4, 9)))
    assert len(days) == 1
    d, content, entries = days[0]
    assert str(d) == "2026-04-08"
    assert "## Bloccanti" in content  # full file content available
    headings = [h for h, _ in entries]
    assert headings == ["SmarTicket - a", "Infomobile - b"]
    bodies = [b for _, b in entries]
    assert "body A" in bodies[0]
    assert "body B" in bodies[1]


def test_iter_diary_days_fence_aware(tmp_diario):
    _day(
        tmp_diario, "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### Real - x\n\n```\n### not a heading\n```\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    from mcp_cronos.utils.scan import iter_diary_days

    _d, _c, entries = next(iter(iter_diary_days(date(2026, 4, 8), date(2026, 4, 8))))
    assert [h for h, _ in entries] == ["Real - x"]  # fenced '### ' not an entry
```
Run `uv run pytest tests/test_scan.py -v` → FAIL (module missing).

- [ ] **Step 2: creare src/mcp_cronos/utils/scan.py**

```python
"""Shared day-by-day diary scanner used by the read/analysis tools.

Yields, for each day in a range that has a diary file, the date, the raw file
content, and the list of (heading, body) pairs for the top-level '### ' entries
(fence-aware). Centralises the scan loop that lista/dossier/statistiche/audit/
riferimento would otherwise each re-implement.
"""

from collections.abc import Iterator
from datetime import date

from mcp_cronos.utils.dates import get_date_range, get_file_path
from mcp_cronos.utils.markdown import split_entries_respecting_fences


def iter_diary_days(start: date, end: date) -> Iterator[tuple[date, str, list[tuple[str, str]]]]:
    """Yield (day, content, entries) for each existing diary file in [start, end].

    entries is a list of (heading, body): heading is the text after '### ' of a
    top-level entry; body is the rest of that entry chunk. Segmentation is
    fence-aware (fenced code blocks are opaque).
    """
    for d in get_date_range(start, end):
        file_path = get_file_path(d)
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        entries: list[tuple[str, str]] = []
        for part in split_entries_respecting_fences(content):
            head_body = part.split("\n", 1)
            first = head_body[0]
            if not first.startswith("### "):
                continue
            heading = first[4:].strip()
            body = head_body[1] if len(head_body) > 1 else ""
            entries.append((heading, body))
        yield d, content, entries
```

- [ ] **Step 3: verify**

Run: `uv run pytest tests/test_scan.py -v` → PASS.
Run: `uv run pytest -q` → verde. `uv run ruff check src/mcp_cronos/utils/scan.py tests/test_scan.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/utils/scan.py tests/test_scan.py
git commit -m "feat(scan): add shared iter_diary_days scanner

CHANGE: New utils/scan.iter_diary_days yields (day, content, entries) for each
existing diary file in a range, with fence-aware (heading, body) entries.
Foundation to de-duplicate the per-day scan loop across the read tools."
```

---

## Task 2: migrare i tool a `iter_diary_days`

**Files:**
- Modify: `src/mcp_cronos/tools/statistiche.py`, `src/mcp_cronos/tools/riferimento.py`, `src/mcp_cronos/tools/dossier.py`, `src/mcp_cronos/tools/audit_progetti.py`, `src/mcp_cronos/tools/reader.py`

**Regola assoluta:** comportamento IDENTICO. NON modificare alcun test. Dopo OGNI tool migrato, eseguire `uv run pytest -q` e confermare 304 verdi. Se un test fallisce, la migrazione di quel tool e' infedele: correggere finche' verde, senza toccare i test.

Per ogni tool: leggere la funzione attuale, sostituire il blocco
`for d in get_date_range(start, end): fp = get_file_path(d); if not fp.exists(): continue; content = fp.read_text(...); for part in split_entries_respecting_fences(content): ...`
con
`for d, content, entries in iter_diary_days(start, end): for heading, body in entries: ...`
e rimuovere gli import ora inutilizzati (`get_date_range`, `get_file_path`, `split_entries_respecting_fences`) SE non piu' usati altrove nel file (mantenere `get_today`/`parse_date` che servono ancora). Aggiungere `from mcp_cronos.utils.scan import iter_diary_days`.

Dettaglio per tool:

- [ ] **Step 1: statistiche.py** — nel loop usa `entries`: `for heading, body in entries: projects = canonical_projects(heading); ...`. `content` non serve (ignorarlo: `for d, _content, entries in iter_diary_days(...)`). `mese = str(d)[:7]` come prima. Verificare 304 verdi.

- [ ] **Step 2: riferimento.py** — il match era su `part.lower()` (intestazione+corpo). Con `(heading, body)`: `if needle not in heading.lower() and needle not in body.lower(): continue`. Poi `projs = canonical_projects(heading)` e raccolta come prima. `content` non serve. Verificare 304 verdi (i test esistenti hanno il needle nel corpo, restano verdi).

- [ ] **Step 3: dossier.py** — per ogni `(heading, body)` matcha `target_set` via `canonical_projects(heading)` come prima; per i bloccanti per-giorno usa `content` gia' fornito: `if day_has_project: diary = parse_diary_content(content); ...` (NON rileggere il file). Mantiene `parse_diary_content` (gia' importato). Verificare 304 verdi.

- [ ] **Step 4: audit_progetti.py** — per ogni `(heading, _body)` usa `project_tokens(heading)` per il clustering come prima. `content`/`body` non servono. Verificare 304 verdi.

- [ ] **Step 5: reader.py (lista_progetti)** — sostituire il loop con `for _d, content, _entries in iter_diary_days(start, end): for proj in extract_projects(content): ...`. `extract_projects(content)` resta la fonte dei progetti per file (comportamento identico). Mantiene `extract_projects` importato; rimuove `get_file_path` se non piu' usato (ATTENZIONE: `leggi_diario` nello stesso file usa ancora `get_file_path` e `get_date_range` — NON rimuovere quegli import, sono usati da leggi_diario). Verificare 304 verdi.

- [ ] **Step 6: verifica finale**

Run: `uv run pytest -q` → 304 verdi, NESSUN test modificato (`git diff --stat` mostra solo file in `src/`, nessun `tests/` a parte test_scan.py del Task 1).
Run: `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` → puliti.

- [ ] **Step 7: commit**

```bash
git add src/mcp_cronos/tools/statistiche.py src/mcp_cronos/tools/riferimento.py src/mcp_cronos/tools/dossier.py src/mcp_cronos/tools/audit_progetti.py src/mcp_cronos/tools/reader.py
git commit -m "refactor(tools): use shared iter_diary_days scanner

CHANGE: statistiche, riferimento, dossier, audit_progetti and lista_progetti now
use utils/scan.iter_diary_days instead of each re-implementing the per-day
read+segment loop. Behaviour unchanged (all existing tests green, untouched);
dossier reuses the already-read content for blockers instead of re-reading."
```

---

## Chiusura
- [ ] **Suite + lint:** `uv run pytest -q` → 304 verdi; `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` puliti.
- [ ] **Verifica sul campo (repo, diario reale):** confermare che dossier/statistiche/riferimento producano gli STESSI risultati di prima (Teseo dossier 201 voci; statistiche Teseo 201; riferimento DVT-552 4 voci):
  `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/Users/mauriziomocci/Documents/workspace/Diario uv run python -c "from mcp_cronos.tools.dossier import dossier_progetto as D; from mcp_cronos.tools.statistiche import statistiche as S; from mcp_cronos.tools.riferimento import traccia_riferimento as R; print('dossier Teseo', D('Teseo', ultimi_giorni=180)['num_voci']); print('stats Teseo', {x['sistema']:x['voci'] for x in S(ultimi_giorni=180)['per_sistema']}.get('Teseo')); print('rif DVT-552', R('DVT-552', ultimi_giorni=180)['num_voci'])"`
  Atteso: dossier Teseo 201, stats Teseo 201, rif DVT-552 4 (invariati).

Branch `refactor/shared-diary-scanner` pronto per il merge.

## Note di esecuzione
- Refactor a comportamento identico: la rete sono i 304 test. Migrare un tool alla volta, eseguire la suite dopo ciascuno.
- NON toccare `extract_projects` ne' `parse_entries` (debito separato).
- `leggi_diario` (in reader.py) NON va migrato (legge per data/range con la sua logica di stub per giorni mancanti); migrare SOLO `lista_progetti`. Quindi gli import `get_file_path`/`get_date_range` restano in reader.py per leggi_diario.
