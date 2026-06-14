# Piano di implementazione — Efficienza token/contesto

> **Per worker agentici:** SUB-SKILL RICHIESTA: usare superpowers:subagent-driven-development per eseguire questo piano task per task. Gli step usano la sintassi a checkbox (`- [ ]`).

**Obiettivo:** ridurre l'output che i tool di Cronos immettono nel contesto, mettendo un tetto configurabile ai risultati di `cerca` (con segnalazione esplicita del troncamento) e rendendo compatto l'output di `leggi_diario` su range (i giorni mancanti diventano una lista di date nel riepilogo, non un oggetto per giorno).

**Architettura:** server MCP sincrono, Python 3.10+. I tool ritornano dict serializzati a JSON. Nessuna modifica al flusso di fine giornata a due fasi.

**Stack:** Python 3.10+, MCP SDK, pytest, ruff.

**Riferimento spec:** `docs/specs/2026-06-14-token-efficiency-design.md`

**Lingua:** codice/commenti/docstring/commit in inglese; piano e spec in italiano.

---

## Struttura dei file toccati

- `src/mcp_cronos/tools/cerca.py` (modifica): parametro `max_risultati`, output cappato con `troncato`/`max_risultati`/`nota`.
- `src/mcp_cronos/server.py` (modifica): `inputSchema` di `cronos_cerca` + dispatch passa `max_risultati`.
- `src/mcp_cronos/tools/reader.py` (modifica): `leggi_diario` non emette stub per giorni mancanti; `riepilogo.date_mancanti`.
- `tests/test_cerca.py` (modifica): test del tetto.
- `tests/test_reader.py` (modifica): aggiornare i due test del contratto + nuovo test `date_mancanti`.
- `README.md` (modifica): documentare i nuovi campi/parametri.

---

## Fase 1 — Tetto sui risultati di `cerca`

### Task 1: test del tetto (test-first)

**Files:**
- Test: `tests/test_cerca.py`

- [ ] **Step 1: scrivere i test che falliscono**

Aggiungere in coda a `tests/test_cerca.py`. Nota: lo stile dei test esistenti crea file diario sotto `tmp_diario`; per indurre piu' match, scrivere un file con piu' entry che contengono lo stesso termine. Usare lo stesso schema dei test esistenti (verificare con una rilettura come creano i file). Esempio autosufficiente:

```python
def test_cerca_caps_results_and_reports_truncation(tmp_diario):
    from mcp_cronos.tools.cerca import cerca_nel_diario

    month_dir = tmp_diario / "2026" / "04"
    month_dir.mkdir(parents=True, exist_ok=True)
    (month_dir / "2026-04-09.md").write_text(
        "# Per lo Stand-up - 10 Aprile 2026\n\n"
        "## Cosa ho fatto ieri\n\n"
        "### Alpha - widget\n\nwidget work\n\n---\n\n"
        "### Beta - widget\n\nwidget work\n\n---\n\n"
        "### Gamma - widget\n\nwidget work\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )

    result = cerca_nel_diario(
        query="widget", data_inizio="2026-04-09", data_fine="2026-04-09",
        tipo=["raw"], max_risultati=2,
    )

    assert result["totale_risultati"] == 3
    assert len(result["risultati"]) == 2
    assert result["troncato"] is True
    assert result["max_risultati"] == 2
    assert "nota" in result


def test_cerca_no_truncation_under_limit(tmp_diario):
    from mcp_cronos.tools.cerca import cerca_nel_diario

    month_dir = tmp_diario / "2026" / "04"
    month_dir.mkdir(parents=True, exist_ok=True)
    (month_dir / "2026-04-09.md").write_text(
        "# Per lo Stand-up - 10 Aprile 2026\n\n"
        "## Cosa ho fatto ieri\n\n"
        "### Alpha - widget\n\nwidget work\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )

    result = cerca_nel_diario(
        query="widget", data_inizio="2026-04-09", data_fine="2026-04-09", tipo=["raw"],
    )

    assert result["troncato"] is False
    assert result["max_risultati"] == 50
    assert "nota" not in result
```

- [ ] **Step 2: eseguire e verificare il fallimento**

Run: `uv run pytest tests/test_cerca.py -k "caps_results or no_truncation" -v`
Atteso: FAIL (parametro/campi non esistono ancora).

- [ ] **Step 3: implementare il tetto in cerca.py**

In `src/mcp_cronos/tools/cerca.py`, cambiare la firma di `cerca_nel_diario` aggiungendo il parametro (dopo `tipo`):

```python
def cerca_nel_diario(
    query: str,
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 90,
    tipo: Optional[list[str]] = None,
    max_risultati: int = 50,
) -> dict:
```

Aggiornare il docstring `Args:` aggiungendo:
```
        max_risultati: Numero massimo di risultati restituiti (default 50).
            La ricerca trova tutti i match ma ne restituisce al piu' questo
            numero; il totale trovato resta in `totale_risultati`.
```

Sostituire il `return` finale:
```python
    return {
        "query": query,
        "periodo": {"da": str(start), "a": str(end)},
        "tipo": sorgenti,
        "files_cercati": files_cercati,
        "totale_risultati": len(risultati),
        "risultati": risultati,
    }
```
con:
```python
    troncato = len(risultati) > max_risultati
    output: dict = {
        "query": query,
        "periodo": {"da": str(start), "a": str(end)},
        "tipo": sorgenti,
        "files_cercati": files_cercati,
        "totale_risultati": len(risultati),
        "max_risultati": max_risultati,
        "troncato": troncato,
        "risultati": risultati[:max_risultati],
    }
    if troncato:
        output["nota"] = (
            f"Trovati {len(risultati)} match, mostrati i primi {max_risultati}. "
            "Restringi il range di date, usa 'tipo' per filtrare le sorgenti, "
            "o aumenta 'max_risultati'."
        )
    return output
```

- [ ] **Step 4: aggiornare la definizione del tool in server.py**

In `src/mcp_cronos/server.py`, nella `Tool(name="cronos_cerca", ...)`, dentro `inputSchema["properties"]` aggiungere:
```python
                "max_risultati": {
                    "type": "integer",
                    "description": "Numero massimo di risultati restituiti (default 50)",
                },
```
E aggiungere una riga alla descrizione testuale dei parametri del tool (nel blocco `description="""..."""`), sotto la riga di `tipo`:
```
- max_risultati (int, optional): Numero massimo di risultati restituiti (default 50)
```
Nel dispatch `call_tool`, nel ramo `elif name == "cronos_cerca":`, aggiungere l'argomento:
```python
                max_risultati=arguments.get("max_risultati", 50),
```

- [ ] **Step 5: verificare**

Run: `uv run pytest tests/test_cerca.py -v` → tutti verdi (inclusi i due nuovi e i preesistenti).
Run: `uv run pytest -q` → suite verde.
Run: `uv run ruff check src/mcp_cronos/tools/cerca.py src/mcp_cronos/server.py tests/test_cerca.py` → pulito.

- [ ] **Step 6: commit**

```bash
git add src/mcp_cronos/tools/cerca.py src/mcp_cronos/server.py tests/test_cerca.py
git commit -m "feat(cerca): cap search results with explicit truncation reporting

CHANGE: cerca_nel_diario accepts max_risultati (default 50); it still counts
all matches in totale_risultati but returns at most max_risultati, adding
troncato and a nota when the result set was capped. Keeps existing fields
backward compatible."
```

---

## Fase 2 — Output compatto di `leggi_diario`

### Task 2: aggiornare i test del contratto + nuovo test (test-first)

**Files:**
- Test: `tests/test_reader.py`

- [ ] **Step 1: leggere i test esistenti**

Aprire `tests/test_reader.py` e individuare i due test che dipendono dagli stub dei giorni mancanti: il test del singolo giorno mancante (asserisce `result["giorni"][0]["esiste"] is False`) e il test del range con un giorno mancante (asserisce `files_trovati == 1` e `files_mancanti == 1`).

- [ ] **Step 2: aggiornare quei due test al nuovo contratto**

Nel test del singolo giorno mancante, sostituire l'asserzione `assert result["giorni"][0]["esiste"] is False` (e qualsiasi accesso a `giorni[0]` per quel giorno) con:
```python
    assert result["giorni"] == []
    assert result["riepilogo"]["files_mancanti"] == 1
    assert result["riepilogo"]["date_mancanti"] == ["<data del test>"]
```
dove `<data del test>` e' la stringa data usata nel test (es. `"2026-04-09"` — usare quella effettivamente presente nel test).

Nel test del range con un giorno mancante, mantenere `files_trovati == 1` e `files_mancanti == 1`, e aggiungere:
```python
    assert len(result["giorni"]) == 1  # solo il giorno esistente
    assert "<data mancante>" in result["riepilogo"]["date_mancanti"]
```
con `<data mancante>` la data del giorno che non esiste nel test.

- [ ] **Step 3: aggiungere un test esplicito su date_mancanti**

```python
def test_leggi_diario_range_lists_missing_days_compactly(sample_diary_it):
    from mcp_cronos.tools.reader import leggi_diario

    # sample_diary_it crea 2026-04-09; 2026-04-08 non esiste
    result = leggi_diario(data_inizio="2026-04-08", data_fine="2026-04-09")

    assert len(result["giorni"]) == 1
    assert result["giorni"][0]["data"] == "2026-04-09"
    assert result["riepilogo"]["files_trovati"] == 1
    assert result["riepilogo"]["files_mancanti"] == 1
    assert result["riepilogo"]["date_mancanti"] == ["2026-04-08"]
    assert all("esiste" not in g for g in result["giorni"])
```
(Verificare che la fixture `sample_diary_it` crei davvero `2026-04-09`; e' definita in `tests/conftest.py`.)

- [ ] **Step 4: eseguire e verificare il fallimento**

Run: `uv run pytest tests/test_reader.py -v`
Atteso: FAIL sui test aggiornati e sul nuovo (campo `date_mancanti` assente, stub ancora presenti).

### Task 3: implementare l'output compatto in reader.py

**Files:**
- Modify: `src/mcp_cronos/tools/reader.py`

- [ ] **Step 1: modificare leggi_diario**

In `src/mcp_cronos/tools/reader.py`, dentro `leggi_diario`, sostituire il blocco di raccolta:
```python
    # Leggi i file
    risultati = []
    files_trovati = 0
    files_mancanti = 0

    for d in dates_to_read:
        file_path = get_file_path(d)

        if file_path.exists():
            files_trovati += 1
            diary = parse_diary_file(file_path)
            if diary:
                entries_data = []
                for entry in diary.entries:
                    entries_data.append(
                        {
                            "progetto": entry.progetto,
                            "descrizione": entry.descrizione,
                            "richiesto_da": entry.richiesto_da,
                            "contenuto_preview": entry.contenuto[:200] + "..."
                            if len(entry.contenuto) > 200
                            else entry.contenuto,
                            "riferimenti": entry.riferimenti,
                        }
                    )

                risultati.append(
                    {
                        "data": str(d),
                        "file": str(file_path),
                        "titolo": diary.titolo,
                        "entries": entries_data,
                        "num_entries": len(diary.entries),
                        "bloccanti": diary.bloccanti,
                    }
                )
        else:
            files_mancanti += 1
            risultati.append(
                {
                    "data": str(d),
                    "file": str(file_path),
                    "esiste": False,
                    "messaggio": "File non trovato",
                }
            )
```
con:
```python
    # Leggi i file. I giorni mancanti non producono un oggetto in `giorni`:
    # finiscono come lista di date in `riepilogo.date_mancanti`, per mantenere
    # l'output compatto su range lunghi e sparsi.
    risultati = []
    date_mancanti: list[str] = []
    files_trovati = 0
    files_mancanti = 0

    for d in dates_to_read:
        file_path = get_file_path(d)

        if file_path.exists():
            files_trovati += 1
            diary = parse_diary_file(file_path)
            if diary:
                entries_data = []
                for entry in diary.entries:
                    entries_data.append(
                        {
                            "progetto": entry.progetto,
                            "descrizione": entry.descrizione,
                            "richiesto_da": entry.richiesto_da,
                            "contenuto_preview": entry.contenuto[:200] + "..."
                            if len(entry.contenuto) > 200
                            else entry.contenuto,
                            "riferimenti": entry.riferimenti,
                        }
                    )

                risultati.append(
                    {
                        "data": str(d),
                        "file": str(file_path),
                        "titolo": diary.titolo,
                        "entries": entries_data,
                        "num_entries": len(diary.entries),
                        "bloccanti": diary.bloccanti,
                    }
                )
        else:
            files_mancanti += 1
            date_mancanti.append(str(d))
```

E sostituire il `return` finale:
```python
    return {
        "periodo": {
            "da": str(dates_to_read[0]),
            "a": str(dates_to_read[-1]),
            "giorni_totali": len(dates_to_read),
        },
        "riepilogo": {"files_trovati": files_trovati, "files_mancanti": files_mancanti},
        "giorni": risultati,
    }
```
con:
```python
    return {
        "periodo": {
            "da": str(dates_to_read[0]),
            "a": str(dates_to_read[-1]),
            "giorni_totali": len(dates_to_read),
        },
        "riepilogo": {
            "files_trovati": files_trovati,
            "files_mancanti": files_mancanti,
            "date_mancanti": date_mancanti,
        },
        "giorni": risultati,
    }
```

- [ ] **Step 2: verificare**

Run: `uv run pytest tests/test_reader.py -v` → verdi (i due aggiornati + il nuovo).
Run: `uv run pytest -q` → suite verde.
Run: `uv run ruff check src/mcp_cronos/tools/reader.py tests/test_reader.py` → pulito.

- [ ] **Step 3: commit**

```bash
git add src/mcp_cronos/tools/reader.py tests/test_reader.py
git commit -m "feat(reader): compact leggi_diario range output for missing days

CHANGE: leggi_diario no longer emits a stub object per missing day; missing
dates are collected in riepilogo.date_mancanti and `giorni` contains only days
with content. Updates the two contract tests and adds a date_mancanti test."
```

---

## Fase 3 — Documentazione

### Task 4: aggiornare il README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: documentare `max_risultati` e i nuovi campi di `cerca` (entrambe le lingue)**

Nella sezione `#### cronos_cerca` (inglese e italiana), aggiungere ai parametri opzionali:
- EN: `- `max_risultati` (int): Maximum number of results returned (default 50).`
- IT: `- `max_risultati` (int): Numero massimo di risultati restituiti (default 50).`
E aggiornare la riga "Returns" per citare che l'output include `totale_risultati` (totale match trovati), `troncato` (booleano) e `risultati` (al piu' `max_risultati`).

- [ ] **Step 2: documentare il nuovo `riepilogo` di `cronos_leggi_diario` (entrambe le lingue)**

Nella sezione `#### cronos_leggi_diario`, aggiornare la riga "Returns" per indicare che il riepilogo include `files_trovati`, `files_mancanti` e `date_mancanti` (lista delle date senza file), e che `giorni` contiene solo i giorni con contenuto.

- [ ] **Step 3: commit**

```bash
git add README.md
git commit -m "docs(readme): document cerca max_risultati and leggi_diario summary

CHANGE: Documents the cerca max_risultati parameter and the troncato/
totale_risultati result fields, and the leggi_diario riepilogo.date_mancanti
field, in both language sections."
```

---

## Chiusura della Fase B

- [ ] **Step finale: suite + lint**

Run: `uv run pytest -q` → tutti verdi.
Run: `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` → puliti.

Branch `feature/token-efficiency` pronto per il merge (decisione dell'utente, mai push automatico).

---

## Note di esecuzione

- Test-first in entrambe le fasi.
- Cambio di contratto di `leggi_diario` dichiarato nella spec: i due test esistenti vanno aggiornati, non aggirati.
- Se emerge un caso non previsto, fermarsi ed escalare invece di inventare.
