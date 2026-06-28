# Diary hygiene (D6) — Piano di implementazione

> **Per worker agentici:** SUB-SKILL: superpowers:subagent-driven-development + test-driven-development. Step a checkbox. Test-first sempre.

**Goal:** nuovo tool sola-lettura `cronos_igiene` (funzione `igiene_diario`) che segnala problemi di igiene del diario con gravita' e suggerimento azionabile, piu' un riepilogo umano. Include il fix debito em-dash in `parse_entries`. Spec: `docs/specs/2026-06-28-diary-hygiene-design.md`.

> **NOTA POST-IMPLEMENTAZIONE (2026-06-28):** il check #1 descritto sotto come `progetto_non_registrato` (un problema per voce) e' stato REDESIGNATO in forma AGGREGATA `voci_non_mappate` (un solo finding con voci/giorni/esempi, delega a `cronos_audit_progetti`) dopo che il field-test ha prodotto 523 problemi per-voce sul diario reale. La forma effettivamente spedita e' quella aggregata: vedi la spec aggiornata (fonte di verita') e i commit `c3ad9ca`/`f9867ba`. Il resto del piano (Task 1, 2, 4, 5 e gli altri 3 check) e' stato eseguito come scritto.

**Tech Stack:** Python 3.10+, pytest, ruff. Inglese nel codice/commit; piano/spec in italiano; docstring in italiano (convenzione del modulo esistente — vedi markdown.py/dossier.py).

## Global Constraints
- PEP8, 100 col, doppi apici, ruff pulito (check + format). Suite sempre verde dopo ogni task.
- Tool count passa a 19. Esempi nel pacchetto NEUTRI (zero nomi di dominio reali nel codice/README; i test possono usare nomi inventati).
- Riusare lo scanner `iter_diary_days`, il calendario `is_working_day`, la risoluzione `canonical_projects`, i path `get_fine_giornata_path`/`has_legacy_file`/`get_file_path` gia' nel pacchetto. NON reimplementare loop per-giorno.

---

## Task 1: `has_unclosed_fence` in markdown.py (DRY refactor della regola fence)

**Files:** Modify `src/mcp_cronos/utils/markdown.py`; Modify `tests/test_markdown.py`.

La regola fence vive oggi dentro `_split_entries_respecting_fences`. Per non duplicarla, ESTRARRE un generatore privato `_iter_with_fence_state(content)` che entrambi consumano. Comportamento di `_split_entries_respecting_fences` IDENTICO (i test esistenti restano verdi, invariati).

- [ ] **Step 1: test-first** — in `tests/test_markdown.py` aggiungere:
```python
def test_has_unclosed_fence():
    from mcp_cronos.utils.markdown import has_unclosed_fence

    assert has_unclosed_fence("```\ncode\n```") is False
    assert has_unclosed_fence("```\ncode") is True
    assert has_unclosed_fence("no fence here") is False
    assert has_unclosed_fence("") is False
    # 4-backtick outer wrapping an inner 3-backtick block, properly closed
    assert has_unclosed_fence("````\n```\ninner\n```\n````") is False
    # 4-backtick outer left open (inner 3-backtick must NOT close it)
    assert has_unclosed_fence("````\n```\ninner\n```") is True
    # tilde fence
    assert has_unclosed_fence("~~~\ncode") is True
```
Run `uv run pytest tests/test_markdown.py -k unclosed -v` → FAIL.

- [ ] **Step 2: refactor + nuova funzione**. In markdown.py, sostituire il corpo di `_split_entries_respecting_fences` introducendo il generatore condiviso:
```python
def _iter_with_fence_state(content: str):
    """Yield (line, in_fence) for each line of content.

    in_fence is True when the line falls inside a fenced code block, using the
    CommonMark-ish rule shared with the splitter: a fence opens on a line of
    >=3 '`' or '~'; it closes only on a later line of the same char, at least
    as long, with no trailing info string. Tracking the fence length lets a
    longer outer fence survive a shorter inner one. in_fence is evaluated after
    toggling on the current line, matching the splitter's original semantics.
    """
    fence_char = ""
    fence_len = 0
    for line in content.split("\n"):
        stripped = line.lstrip()
        if stripped and stripped[0] in ("`", "~"):
            ch = stripped[0]
            run = len(stripped) - len(stripped.lstrip(ch))
            if run >= 3:
                if not fence_char:
                    fence_char = ch
                    fence_len = run
                elif ch == fence_char and run >= fence_len and stripped[run:].strip() == "":
                    fence_char = ""
                    fence_len = 0
        yield line, bool(fence_char)


def _split_entries_respecting_fences(content: str) -> list[str]:
    """Split content into entry chunks at top-level '### ' headings only.

    Lines inside fenced code blocks are opaque: a '### ' or '---' line inside a
    fence does not start or end an entry. Fence handling lives in
    _iter_with_fence_state (shared with has_unclosed_fence).
    """
    parts: list[str] = []
    current: list[str] = []
    for line, in_fence in _iter_with_fence_state(content):
        if not in_fence and line.startswith("### ") and current:
            parts.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        parts.append("\n".join(current))
    return parts


def has_unclosed_fence(content: str) -> bool:
    """True if a fenced code block is left open at end of content.

    An unclosed fence breaks entry segmentation for the whole file: every later
    entry merges into the open block and disappears from the analysis tools.
    Reuses the shared fence rule via _iter_with_fence_state.
    """
    state = False
    for _line, in_fence in _iter_with_fence_state(content):
        state = in_fence
    return state
```
Mantenere il `split_entries_respecting_fences = _split_entries_respecting_fences` re-export esistente.

- [ ] **Step 3: verify** — `uv run pytest tests/test_markdown.py -v` verde (incl. i test fence esistenti, invariati); `uv run pytest -q` verde; `uv run ruff check src/mcp_cronos/utils/markdown.py tests/test_markdown.py` pulito.

- [ ] **Step 4: commit**
```
feat(markdown): add has_unclosed_fence, share fence rule via generator

CHANGE: Extract _iter_with_fence_state so _split_entries_respecting_fences and
the new has_unclosed_fence share one fence-tracking rule instead of duplicating
it. has_unclosed_fence reports a code block left open at end of content (which
otherwise silently merges all later entries). Splitter behaviour unchanged.
```

---

## Task 2: fix em-dash in `parse_entries` (debito)

**Files:** Modify `src/mcp_cronos/utils/markdown.py`; Modify `tests/test_markdown.py`.

`parse_entries` splitta l'intestazione solo su `" - "`. Allinearlo all'em-dash `" — "` (gia' gestito da project_tokens/canonical_projects altrove).

- [ ] **Step 1: test-first**:
```python
def test_parse_entries_splits_emdash_heading():
    from mcp_cronos.utils.markdown import parse_entries

    entries = parse_entries("### Alpha — descrizione lunga\n\ncorpo\n")
    assert entries[0].progetto == "Alpha"
    assert entries[0].descrizione == "descrizione lunga"
```
Run → FAIL (progetto sarebbe "Alpha — descrizione lunga").

- [ ] **Step 2: fix**. In `parse_entries`, dove oggi fa:
```python
        if " - " in header:
            progetto, descrizione = header.split(" - ", 1)
        else:
            progetto = header
            descrizione = ""
```
sostituire con uno split che accetta sia `" - "` sia `" — "` sul PRIMO separatore che compare:
```python
        progetto, descrizione = _split_heading(header)
```
e aggiungere helper privato vicino a parse_entries:
```python
def _split_heading(header: str) -> tuple[str, str]:
    """Split an entry heading into (project, description).

    Accepts both the ASCII " - " and the em-dash " — " separators; splits on
    whichever appears first. No separator -> the whole header is the project.
    """
    candidates = [header.find(" - "), header.find(" — ")]
    positions = [c for c in candidates if c != -1]
    if not positions:
        return header.strip(), ""
    idx = min(positions)
    sep_len = 3  # both " - " and " — " are 3 chars
    return header[:idx].strip(), header[idx + sep_len:].strip()
```
(`—` = em-dash. Entrambi i separatori sono lunghi 3 caratteri: spazio + simbolo + spazio.)

- [ ] **Step 3: verify** — `uv run pytest tests/test_markdown.py -v` verde (i test esistenti con `" - "` restano verdi); `uv run pytest -q` verde; ruff pulito.

- [ ] **Step 4: commit**
```
fix(markdown): split entry headings on em-dash too

CHANGE: parse_entries now splits "Project — Description" headings on the
em-dash separator, not only the ASCII " - ". Aligns with canonical_projects,
which already handles em-dash; previously an em-dash heading kept the whole
string as the project name.
```

---

## Task 3: `tools/igiene.py` — `igiene_diario`

**Files:** Create `src/mcp_cronos/tools/igiene.py`; Create `tests/test_igiene.py`.

Sola lettura. 4 check, gravita', suggerimento, riepilogo umano, cap. Risoluzione periodo come `tools/riferimento.py` (data_inizio/data_fine sovrascrivono ultimi_giorni; usa get_today/parse_date/timedelta). LEGGERE riferimento.py per copiarne ESATTAMENTE lo schema di risoluzione periodo e di clamp.

Costanti:
```python
_GRAVITA = {
    "fence_non_chiusa": "critico",
    "progetto_non_registrato": "avviso",
    "giorno_lavorativo_mancante": "info",
    "chiusura_mancante": "info",
}
_SUGGERIMENTI = {
    "progetto_non_registrato": (
        "Intestazione non mappata ad alcun progetto del registro: questa voce non "
        "compare in dossier/statistiche. Aggiungi un alias in [cronos.projects], "
        "oppure rilancia cronos_audit_progetti per rigenerare la bozza."
    ),
    "fence_non_chiusa": (
        "Chiudi il blocco con una riga di soli backtick (```): finche' resta aperto, "
        "tutte le voci successive di quel giorno si fondono e spariscono dalle analitiche."
    ),
    "giorno_lavorativo_mancante": (
        "Se era una giornata di ferie/malattia ignora; altrimenti il giorno non e' tracciato."
    ),
    "chiusura_mancante": (
        "Giornata aperta e mai chiusa: usa cronos_scrivi_fine_giornata per chiuderla."
    ),
}
_ORDINE_GRAVITA = {"critico": 0, "avviso": 1, "info": 2}
# etichette per il riepilogo umano: tipo -> (singolare, plurale)
_ETICHETTE = {
    "fence_non_chiusa": ("fence aperta", "fence aperte"),
    "progetto_non_registrato": ("voce fuori registro", "voci fuori registro"),
    "giorno_lavorativo_mancante": ("giorno feriale senza diario", "giorni feriali senza diario"),
    "chiusura_mancante": ("giornata non chiusa", "giornate non chiuse"),
}
```
Helper problema:
```python
def _problema(tipo: str, d, dettaglio: str) -> dict:
    return {
        "tipo": tipo,
        "gravita": _GRAVITA[tipo],
        "data": str(d),
        "dettaglio": dettaglio,
        "suggerimento": _SUGGERIMENTI[tipo],
    }
```
Logica:
```python
def igiene_diario(data_inizio=None, data_fine=None, ultimi_giorni=180, max_problemi=100):
    # ... risoluzione periodo identica a riferimento.py -> start, end
    if max_problemi < 0:
        max_problemi = 0
    config = load_config()
    registro_attivo = config.projects_registered
    problemi: list[dict] = []
    note: list[str] = []

    # Pass 1: giorni con file (scanner): fence, progetto non registrato, chiusura mancante
    for d, content, entries in iter_diary_days(start, end):
        if has_unclosed_fence(content):
            problemi.append(_problema("fence_non_chiusa", d, "blocco di codice aperto a fine file"))
        if registro_attivo:
            for heading, _body in entries:
                if not canonical_projects(heading):
                    problemi.append(_problema("progetto_non_registrato", d, heading[:120]))
        if not has_legacy_file(d) and not get_fine_giornata_path(d).exists():
            problemi.append(
                _problema("chiusura_mancante", d, "raw.md presente, fine-giornata.md assente")
            )

    # Pass 2: giorni lavorativi senza alcun file (festivo-aware)
    for d in get_date_range(start, end):
        if is_working_day(d) and not get_file_path(d).exists():
            problemi.append(_problema("giorno_lavorativo_mancante", d, "giorno lavorativo senza diario"))

    if not registro_attivo:
        note.append("registro vuoto: check progetto_non_registrato saltato")

    conteggi = {t: 0 for t in _GRAVITA}
    conteggi_gravita = {"critico": 0, "avviso": 0, "info": 0}
    for p in problemi:
        conteggi[p["tipo"]] += 1
        conteggi_gravita[p["gravita"]] += 1
    totale = len(problemi)

    problemi.sort(key=lambda p: (_ORDINE_GRAVITA[p["gravita"]], p["data"]))
    troncato = totale > max_problemi
    problemi_out = problemi[:max_problemi]

    return {
        "periodo": {"da": str(start), "a": str(end), "giorni_analizzati": (end - start).days + 1},
        "registro_attivo": registro_attivo,
        "riepilogo": _riepilogo(totale, conteggi_gravita, conteggi),
        "problemi": problemi_out,
        "conteggi": conteggi,
        "conteggi_gravita": conteggi_gravita,
        "totale_problemi": totale,
        "max_problemi": max_problemi,
        "troncato": troncato,
        "note": note,
    }
```
`_riepilogo`:
```python
def _riepilogo(totale: int, conteggi_gravita: dict, conteggi: dict) -> str:
    if totale == 0:
        return "Nessun problema rilevato nel periodo."
    sev = (
        f"{conteggi_gravita['critico']} critici, "
        f"{conteggi_gravita['avviso']} avvisi, "
        f"{conteggi_gravita['info']} info"
    )
    frammenti = []
    for tipo, (sing, plur) in _ETICHETTE.items():
        n = conteggi[tipo]
        if n:
            frammenti.append(f"{n} {sing if n == 1 else plur}")
    coda = " — " + ", ".join(frammenti) if frammenti else ""
    plur_prob = "problema" if totale == 1 else "problemi"
    return f"{totale} {plur_prob}: {sev}{coda}."
```

- [ ] **Step 1: test-first** — `tests/test_igiene.py`. Usa la fixture `tmp_diario` e un helper `_day` come in test_scan.py (cartella `{y}/{m}/{ymd}/raw.md`). Test (almeno):
  - `test_progetto_non_registrato_segnalato`: con `cronos.toml` che registra un progetto noto (es. "Alpha"), una voce `### Alpha - x` non e' segnalata, una `### Sconosciuto - y` SI (tipo progetto_non_registrato, gravita avviso). Per popolare il registro nel test, scrivere un `cronos.toml` nella tmp e puntare la config li' — REPLICARE il meccanismo usato dai test esistenti di lista_progetti/dossier che gia' testano il registro (cercare in tests/ come viene impostato `[cronos.projects]`/`projects_registered` nei test; riusare quel pattern, non inventarne uno nuovo).
  - `test_registro_vuoto_salta_check`: senza registro, nessun progetto_non_registrato + nota "registro vuoto...".
  - `test_fence_non_chiusa_critico`: giorno con fence aperta -> problema critico; giorno pulito -> no.
  - `test_giorno_lavorativo_mancante`: buco feriale -> segnalato; weekend/festivo senza file -> NO (usa una data feriale e una di weekend note).
  - `test_chiusura_mancante_solo_layout_nuovo`: layout nuovo con raw senza fine-giornata -> segnalato; con fine-giornata -> no.
  - `test_cap_e_conteggi_totali`: con max_problemi piccolo, len(problemi) <= max, troncato True, ma conteggi restano totali.
  - `test_riepilogo_umano`: totale 0 -> "Nessun problema rilevato nel periodo."; con problemi -> stringa con conteggi.
  Run → FAIL (modulo assente).

- [ ] **Step 2: implementare** `tools/igiene.py` come sopra. Import: `iter_diary_days` (scan), `has_unclosed_fence` (markdown), `canonical_projects` (projects), `is_working_day` (workdays), `get_today/parse_date/get_date_range/get_file_path/get_fine_giornata_path/has_legacy_file` (dates), `load_config` (config), `timedelta` (datetime).

- [ ] **Step 3: verify** — `uv run pytest tests/test_igiene.py -v` verde; `uv run pytest -q` verde; ruff pulito (check + format).

- [ ] **Step 4: commit**
```
feat(igiene): add cronos_igiene diary hygiene advisor

CHANGE: New tools/igiene.igiene_diario scans the diary read-only and reports
hygiene problems with a severity and an actionable suggestion each, plus a
human-readable summary. Checks: entry headings that resolve to no registered
project (invisible to dossier/stats), unclosed code fences (corrupt a day),
missing working days, and days opened but never closed. Output is capped while
per-type and per-severity counts stay total.
```

---

## Task 4: registrare `cronos_igiene` in server.py

**Files:** Modify `src/mcp_cronos/server.py`.

- [ ] **Step 1** — LEGGERE come `cronos_riferimento` e' registrato (Tool schema in list_tools + branch in call_tool). Replicare per `cronos_igiene`:
  - Schema input: `data_inizio` (string, opz., YYYY-MM-DD), `data_fine` (string, opz.), `ultimi_giorni` (integer, default 180), `max_problemi` (integer, default 100). Nessun required. Description neutra in italiano (es. "Controllo di igiene del diario: segnala voci fuori registro, fence non chiuse, giorni feriali mancanti e giornate non chiuse, con gravita' e suggerimento.").
  - Branch dispatch:
```python
elif name == "cronos_igiene":
    result = igiene_diario(
        data_inizio=arguments.get("data_inizio"),
        data_fine=arguments.get("data_fine"),
        ultimi_giorni=arguments.get("ultimi_giorni", 180),
        max_problemi=arguments.get("max_problemi", 100),
    )
```
  - Import in cima: `from mcp_cronos.tools.igiene import igiene_diario`.

- [ ] **Step 2: verify** — `uv run pytest -q` verde. Se esiste un test che conta i tool (cercare in tests/ un assert sul numero di tool, es. test_server), aggiornarlo a 19. `uv run python -c "import asyncio; from mcp_cronos.server import list_tools; print(len(asyncio.run(list_tools())))"` -> 19 (o l'equivalente gia' usato nei test). ruff pulito.

- [ ] **Step 3: commit**
```
feat(server): register cronos_igiene tool (19 tools)

CHANGE: Expose igiene_diario as the cronos_igiene MCP tool with an optional
date window and max_problemi cap.
```

---

## Task 5: documentazione (regola fissa) + onboarding

**Files:** Modify `README.md`, `README.en.md` (o i nomi reali dei due README — VERIFICARE), `CLAUDE.md`, `CHANGELOG.md`.

- [ ] **Step 1: README in ENTRAMBE le lingue** — VERIFICARE i nomi dei due file README (it/en) leggendo la root. Per ciascuno:
  - aggiungere sezione `#### cronos_igiene` con descrizione, parametri e un esempio NEUTRO di output (nomi inventati tipo "Alpha"/"Beta", nessun nome di dominio reale);
  - aggiungere una sezione "Per iniziare" / "Getting started" coi 4 passi del ciclo audit->registro->igiene (vedi spec, sezione "Aiuto all'utente e usabilita'"): scrivi voci -> `cronos_audit_progetti` genera la bozza `[cronos.projects]` -> incolla in `cronos.toml` -> `cronos_igiene` verifica. Linguaggio semplice, valido per qualunque utente.
  - aggiornare il conteggio tool (19) ovunque compaia.

- [ ] **Step 2: CLAUDE.md** — aggiornare tool count a 19, aggiungere `igiene` allo scope/elenco tool e all'albero dei file (`tools/igiene.py`).

- [ ] **Step 3: CHANGELOG.md** — sotto `## [Unreleased]`, sezione `### Added`: voce per `cronos_igiene` (advisor di igiene con gravita'/suggerimento/riepilogo) e nota della guida "Per iniziare"; sezione `### Fixed`: parse_entries em-dash. NON finalizzare la versione (lo fa il rilascio).

- [ ] **Step 4: verify** — `uv run pytest -q` verde; `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` pulito. Rileggere le due sezioni README per coerenza EN/IT.

- [ ] **Step 5: commit**
```
docs: document cronos_igiene and add getting-started workflow

CHANGE: README (both languages) gains a cronos_igiene section with a neutral
example and a 4-step getting-started flow (audit -> registry -> igiene) that
makes building the project list simple for any user. CLAUDE.md tool count 19;
CHANGELOG Unreleased records the tool and the parse_entries em-dash fix.
```

---

## Chiusura
- [ ] **Suite + lint:** `uv run pytest -q` verde; `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` puliti.
- [ ] **Verifica sul campo (diario reale):**
  `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/Users/mauriziomocci/Documents/workspace/Diario uv run python -c "from mcp_cronos.tools.igiene import igiene_diario as I; r=I(ultimi_giorni=180); print(r['riepilogo']); print(r['conteggi']); print([p['dettaglio'] for p in r['problemi'] if p['tipo']=='progetto_non_registrato'][:5])"`
  Attendersi: voci tipo "Supporto / Ticket Odoo ..." tra i progetto_non_registrato (lavoro reale invisibile alle analitiche), conteggi plausibili, riepilogo leggibile.
- [ ] Review (spec-compliance + qualita') prima del merge.

Branch `feature/diary-hygiene`.

## Note di esecuzione
- Test-first ogni task. Suite verde dopo ciascuno. Mai modificare i test esistenti per farli passare (Task 1 e' un refactor a comportamento identico).
- Per il registro nei test (Task 3): RIUSARE il meccanismo gia' presente nei test del registro (lista_progetti/dossier) — non inventare un nuovo modo di popolare `[cronos.projects]`.
- Niente nomi di dominio reali nel codice/README spediti.
