# Cronos MCP Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendere Cronos generico (rimuovere riferimenti a "Domenico"), eliminare la generazione Slack hardcoded, rendere il path configurabile solo via env var, e aggiungere 3 nuovi tool (cerca, settimana, aggiungi_a_progetto).

**Architecture:** MCP server Python con tool registrati in `server.py`. Ogni tool e' un modulo in `tools/`. Le utility condivise sono in `utils/`. La config legge `CRONOS_DIARIO_PATH` da env var (obbligatoria, nessun default).

**Tech Stack:** Python 3.10+, mcp>=1.0.0, pydantic>=2.0.0

---

## File Structure

```
src/mcp_cronos/
  config.py              — MODIFY: rimuovere default hardcoded, errore se env var mancante
  server.py              — MODIFY: rimuovere tool slack, aggiungere 3 nuovi tool, aggiornare descrizioni
  templates.py           — nessuna modifica
  tools/
    slack.py             — DELETE: tool con logica hardcoded fragile
    standup.py           — MODIFY: rimuovere riferimenti "Domenico", aggiornare istruzioni stile
    fine_giornata.py     — MODIFY: rimuovere "Domenico", fix riferimento tool inesistente
    consolida.py         — MODIFY: rimuovere riferimento "Domenico"
    entries.py           — nessuna modifica
    reader.py            — nessuna modifica
    cerca.py             — CREATE: ricerca full-text nel diario
    settimana.py         — CREATE: riassunto settimanale per progetto
    aggiungi_progetto.py — CREATE: append intelligente a entry esistente
  utils/
    markdown.py          — nessuna modifica
    dates.py             — nessuna modifica
```

---

### Task 1: Config — rimuovere default hardcoded

**Files:**
- Modify: `src/mcp_cronos/config.py`

- [ ] **Step 1: Modificare `config.py`**

Rimuovere `DEFAULT_DIARIO_PATH` e rendere `CRONOS_DIARIO_PATH` obbligatoria:

```python
"""
Configurazione per MCP Cronos.

Il path del diario viene letto dalla variabile d'ambiente CRONOS_DIARIO_PATH.
La variabile e' obbligatoria.
"""

import os
from pathlib import Path


def get_diario_path() -> Path:
    """
    Restituisce il path del diario.

    Legge dalla variabile d'ambiente CRONOS_DIARIO_PATH.

    Returns:
        Path del diario di lavoro

    Raises:
        RuntimeError: Se CRONOS_DIARIO_PATH non e' impostata
    """
    path_str = os.environ.get("CRONOS_DIARIO_PATH")
    if not path_str:
        raise RuntimeError(
            "Variabile d'ambiente CRONOS_DIARIO_PATH non impostata. "
            "Imposta il path del diario di lavoro, es: "
            "CRONOS_DIARIO_PATH=/path/to/Diario"
        )
    return Path(path_str)


def ensure_diario_exists() -> bool:
    """
    Verifica che il path del diario esista.

    Returns:
        True se esiste, False altrimenti
    """
    return get_diario_path().exists()
```

- [ ] **Step 2: Verificare che il server parta**

Run: `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/tmp/test-diario uv run python -c "from mcp_cronos.config import get_diario_path; print(get_diario_path())"`
Expected: `/tmp/test-diario`

- [ ] **Step 3: Verificare errore senza env var**

Run: `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && unset CRONOS_DIARIO_PATH && uv run python -c "from mcp_cronos.config import get_diario_path; get_diario_path()" 2>&1 || true`
Expected: `RuntimeError: Variabile d'ambiente CRONOS_DIARIO_PATH non impostata`

- [ ] **Step 4: Commit**

```bash
cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos
git add src/mcp_cronos/config.py
git commit -m "refactor: rendi CRONOS_DIARIO_PATH obbligatoria, rimuovi default hardcoded"
```

---

### Task 2: Eliminare tool Slack hardcoded

**Files:**
- Delete: `src/mcp_cronos/tools/slack.py`
- Modify: `src/mcp_cronos/server.py`

- [ ] **Step 1: Eliminare `slack.py`**

```bash
rm src/mcp_cronos/tools/slack.py
```

- [ ] **Step 2: Rimuovere da `server.py` l'import e il tool**

In `server.py`, rimuovere:
- La riga `from mcp_cronos.tools.slack import genera_slack_domenico`
- L'intero blocco `Tool(name="cronos_genera_slack_domenico", ...)` dall'array `TOOLS`
- Il blocco `elif name == "cronos_genera_slack_domenico":` dal handler `call_tool`

- [ ] **Step 3: Aggiornare il docstring del modulo `server.py`**

Rimuovere la riga `- Generare messaggi Slack per Domenico` dal docstring iniziale.

- [ ] **Step 4: Verificare che il server compili**

Run: `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/tmp uv run python -c "from mcp_cronos.server import server; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos
git add -A
git commit -m "refactor: rimuovi tool cronos_genera_slack_domenico con logica hardcoded"
```

---

### Task 3: Rename Domenico -> standup in `standup.py`

**Files:**
- Modify: `src/mcp_cronos/tools/standup.py`

- [ ] **Step 1: Aggiornare docstring e costante STILE_RIASSUNTO**

Nel docstring del modulo, sostituire ogni occorrenza di "Domenico" con "standup".

In `STILE_RIASSUNTO`, modificare:
- `"Messaggio Slack per un collega (Domenico)"` -> `"Messaggio discorsivo per lo standup"`
- `"Apri con \"Ciao Domenico,\" (sempre)"` -> rimuovere questa riga
- `"Ciao Domenico,"` nell'esempio -> rimuovere il saluto iniziale dall'esempio
- `"Scrivi messaggio per Domenico"` nella lista trigger -> rimuovere

L'intero `STILE_RIASSUNTO` diventa:

```python
STILE_RIASSUNTO = """
ISTRUZIONI PER LA GENERAZIONE DEL RIASSUNTO:

Genera un messaggio discorsivo per lo standup. Lo stile deve essere:

1. **Fluido e naturale** - frasi discorsive, non elenchi puntati rigidi
2. **Alto livello** - racconta cosa hai fatto e perche', non come. Niente dettagli implementativi (niente nomi di file, classi, funzioni, numeri di MR, codici Jira specifici). Menziona solo il concetto generale
3. **Diretto** - vai subito al punto
4. **Niente elenchi puntati** - preferisci frasi fluide e paragrafi brevi
5. **Dettagli tecnici solo se interessanti** - se c'e' una scoperta, un insight o qualcosa di utile per decisioni future, menzionalo brevemente. Altrimenti ometti
6. **Niente strumenti interni** - non menzionare MCP, tool CLI, script interni, automazioni personali
7. **Includi i bloccanti** se ci sono (alla fine, in modo naturale)

STRUTTURA TIPO:
- Un paragrafo per progetto/area con **Nome Progetto** in grassetto all'inizio
- Continuita' discorsiva tra i paragrafi, non elenchi isolati
- Se ci sono ticket di supporto, menzionali brevemente
- Eventuali bloccanti alla fine, in modo discorsivo

ESEMPIO DI TONO:
"Ieri ho dedicato la giornata a Pollicino, lato Keycloak. Ho pianificato e implementato l'integrazione SSO
per la dashboard backoffice, con la possibilita' di accendere o spegnere la funzionalita' tramite un flag
cosi' Pollicino resta utilizzabile anche come modulo singolo.

Sul fronte supporto, e' arrivato un ticket per un validatore con lo schermo bianco su un autobus.
L'ho assegnato a Gavino."

COSA EVITARE:
- Elenchi puntati freddi
- Dettagli di implementazione (nomi di file, classi, numeri di MR/ticket)
- Linguaggio burocratico ("Si comunica che...", "Come da accordi...")
- Convenevoli e formule di cortesia
- Firme o saluti finali
- Riferimenti a strumenti interni o automazioni
""".strip()
```

- [ ] **Step 2: Aggiornare la descrizione del tool in `server.py`**

In `server.py`, il blocco `Tool(name="cronos_riassunto_standup", ...)`: aggiornare la description rimuovendo ogni riferimento a "Domenico" e "Slack". Deve diventare:

```python
Tool(
    name="cronos_riassunto_standup",
    description="""Genera un riassunto discorsivo del diario per lo standup.

Restituisce il contenuto completo delle entry del diario insieme a istruzioni
di stile per generare un messaggio alto livello, fluido e professionale.

Stile del riassunto:
- Alto livello, niente dettagli implementativi
- Fluido e naturale, frasi discorsive, no elenchi puntati
- Niente numeri di MR, codici Jira, nomi di file o classi
- Niente strumenti interni (MCP, tool CLI, script)
- Dettagli tecnici solo se interessanti per decisioni future

Usa questo tool quando l'utente chiede:
- Un riassunto per lo standup / stand-up
- "Cosa dico allo standup?"
- "Riassumi cosa ho fatto [data]"
- "Fammi un riassunto discorsivo"

Parametri:
- data (str, optional): Data singola YYYY-MM-DD (default: ultimo giorno lavorativo)
- data_inizio (str, optional): Data inizio range YYYY-MM-DD
- data_fine (str, optional): Data fine range YYYY-MM-DD

Restituisce: Contenuto del diario con istruzioni di stile per la generazione del messaggio.""",
    inputSchema={...}  # invariato
),
```

- [ ] **Step 3: Commit**

```bash
cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos
git add src/mcp_cronos/tools/standup.py src/mcp_cronos/server.py
git commit -m "refactor: rinomina riferimenti Domenico in standup"
```

---

### Task 4: Rename Domenico -> standup in `fine_giornata.py`

**Files:**
- Modify: `src/mcp_cronos/tools/fine_giornata.py`
- Modify: `src/mcp_cronos/server.py`

- [ ] **Step 1: Aggiornare `STILE_FINE_GIORNATA`**

Modifiche nella costante:
1. Nella struttura del file: `## Messaggio per Domenico` -> `## Messaggio per lo standup`
2. `{messaggio_domenico}` -> `{messaggio_standup}`
3. `=== SEZIONE 4: MESSAGGIO PER DOMENICO ===` -> `=== SEZIONE 4: MESSAGGIO PER LO STANDUP ===`
4. Rimuovere `Apri SEMPRE con "Ciao Domenico,"` e `"Ciao Domenico,"` dall'esempio
5. Sostituire `"Messaggio Slack per Domenico"` -> `"Messaggio discorsivo per lo standup"`
6. Rimuovere il riferimento a `cronos_scrivi_fine_giornata` dalla description del tool. Nella PROCEDURA, step 5 diventa: `5. Scrivi il file al path indicato nel campo 'file'`

- [ ] **Step 2: Aggiornare docstring del modulo**

```python
"""
Tool per la chiusura di fine giornata del diario.

Legge le entry grezze del giorno e restituisce istruzioni per:
1. Riscriverle in ordine cronologico/logico
2. Generare riassunto della giornata
3. Generare riassunto tecnico
4. Generare messaggio per lo standup

L'LLM genera i quattro output e scrive il file completo direttamente.
"""
```

- [ ] **Step 3: Aggiornare description del tool in `server.py`**

Nel blocco `Tool(name="cronos_fine_giornata", ...)`, aggiornare la description:
- `4. Messaggio per Domenico (stile Slack, alto livello)` -> `4. Messaggio per lo standup (alto livello, discorsivo)`
- Rimuovere `Dopo aver generato i quattro output, chiama cronos_scrivi_fine_giornata per scrivere il file.`

- [ ] **Step 4: Commit**

```bash
cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos
git add src/mcp_cronos/tools/fine_giornata.py src/mcp_cronos/server.py
git commit -m "refactor: rinomina Domenico in standup in fine_giornata"
```

---

### Task 5: Rename Domenico -> standup in `consolida.py`

**Files:**
- Modify: `src/mcp_cronos/tools/consolida.py`

- [ ] **Step 1: Aggiornare `STILE_CONSOLIDAMENTO`**

Nel punto 7, sostituire:
```
"Messaggio per Domenico"
```
con:
```
"Messaggio per lo standup"
```

- [ ] **Step 2: Commit**

```bash
cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos
git add src/mcp_cronos/tools/consolida.py
git commit -m "refactor: rinomina Domenico in standup in consolida"
```

---

### Task 6: Nuovo tool `cronos_cerca`

**Files:**
- Create: `src/mcp_cronos/tools/cerca.py`
- Modify: `src/mcp_cronos/server.py`

- [ ] **Step 1: Creare `cerca.py`**

```python
"""
Tool per la ricerca full-text nel diario.

Cerca un pattern testuale nelle entry del diario e restituisce
i match con data, progetto e contesto.
"""

import re
from datetime import timedelta
from typing import Optional

from mcp_cronos.utils.dates import get_file_path, get_today, parse_date, get_date_range
from mcp_cronos.utils.markdown import parse_diary_file


def cerca_nel_diario(
    query: str,
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 90,
) -> dict:
    """
    Cerca un pattern testuale nelle entry del diario.

    Args:
        query: Testo da cercare (case-insensitive, supporta regex)
        data_inizio: Data inizio range YYYY-MM-DD
        data_fine: Data fine range YYYY-MM-DD
        ultimi_giorni: Giorni da cercare se non specificate le date (default 90)

    Returns:
        Dict con risultati della ricerca
    """
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

    dates_to_search = get_date_range(start, end)

    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error as e:
        return {"errore": f"Pattern regex non valido: {e}"}

    risultati = []
    files_cercati = 0

    for d in dates_to_search:
        file_path = get_file_path(d)
        if not file_path.exists():
            continue

        files_cercati += 1
        diary = parse_diary_file(file_path)
        if not diary:
            continue

        for entry in diary.entries:
            # Cerca nel progetto, descrizione e contenuto
            testo_completo = f"{entry.progetto} {entry.descrizione} {entry.contenuto}"
            matches = pattern.findall(testo_completo)

            if matches:
                # Estrai contesto attorno al primo match
                match_obj = pattern.search(testo_completo)
                if match_obj:
                    start_ctx = max(0, match_obj.start() - 100)
                    end_ctx = min(len(testo_completo), match_obj.end() + 100)
                    contesto = testo_completo[start_ctx:end_ctx]
                    if start_ctx > 0:
                        contesto = "..." + contesto
                    if end_ctx < len(testo_completo):
                        contesto = contesto + "..."
                else:
                    contesto = ""

                risultati.append({
                    "data": str(d),
                    "progetto": entry.progetto,
                    "descrizione": entry.descrizione,
                    "num_match": len(matches),
                    "contesto": contesto,
                    "richiesto_da": entry.richiesto_da,
                })

    return {
        "query": query,
        "periodo": {"da": str(start), "a": str(end)},
        "files_cercati": files_cercati,
        "totale_risultati": len(risultati),
        "risultati": risultati,
    }
```

- [ ] **Step 2: Aggiungere il tool in `server.py`**

Aggiungere l'import:
```python
from mcp_cronos.tools.cerca import cerca_nel_diario
```

Aggiungere la definizione Tool nell'array TOOLS:
```python
Tool(
    name="cronos_cerca",
    description="""Cerca testo nelle entry del diario.

Ricerca full-text case-insensitive con supporto regex.
Utile per trovare quando si e' lavorato su un progetto, ticket, argomento.

Usa questo tool quando l'utente chiede:
- "Quando ho lavorato su X?"
- "Cerca nel diario Y"
- "Trova il ticket Z"
- "In quali giorni ho toccato il progetto W?"

Parametri:
- query (str, required): Testo da cercare (case-insensitive, supporta regex)
- data_inizio (str, optional): Data inizio range YYYY-MM-DD
- data_fine (str, optional): Data fine range YYYY-MM-DD
- ultimi_giorni (int, optional): Giorni da cercare (default 90)

Restituisce: Lista di match con data, progetto, contesto.""",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Testo da cercare (supporta regex)"
            },
            "data_inizio": {
                "type": "string",
                "description": "Data inizio YYYY-MM-DD"
            },
            "data_fine": {
                "type": "string",
                "description": "Data fine YYYY-MM-DD"
            },
            "ultimi_giorni": {
                "type": "integer",
                "description": "Giorni da cercare (default 90)"
            }
        },
        "required": ["query"]
    }
),
```

Aggiungere il handler in `call_tool`:
```python
elif name == "cronos_cerca":
    result = cerca_nel_diario(
        query=arguments["query"],
        data_inizio=arguments.get("data_inizio"),
        data_fine=arguments.get("data_fine"),
        ultimi_giorni=arguments.get("ultimi_giorni", 90),
    )
```

- [ ] **Step 3: Verificare che compili**

Run: `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/tmp uv run python -c "from mcp_cronos.tools.cerca import cerca_nel_diario; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos
git add src/mcp_cronos/tools/cerca.py src/mcp_cronos/server.py
git commit -m "feat: aggiungi tool cronos_cerca per ricerca full-text nel diario"
```

---

### Task 7: Nuovo tool `cronos_settimana`

**Files:**
- Create: `src/mcp_cronos/tools/settimana.py`
- Modify: `src/mcp_cronos/server.py`

- [ ] **Step 1: Creare `settimana.py`**

```python
"""
Tool per il riassunto settimanale del diario.

Raggruppa il lavoro della settimana per progetto, mostrando
quanti giorni si e' lavorato su ciascuno e un riepilogo delle attivita'.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.utils.dates import get_file_path, get_today, parse_date, get_date_range
from mcp_cronos.utils.markdown import parse_diary_file


def riassunto_settimana(
    data: Optional[str] = None,
) -> dict:
    """
    Genera un riassunto settimanale raggruppato per progetto.

    Prende la settimana (lun-ven) che contiene la data specificata.

    Args:
        data: Una data nella settimana da analizzare YYYY-MM-DD (default: settimana corrente)

    Returns:
        Dict con riassunto settimanale per progetto
    """
    if data:
        try:
            ref_date = parse_date(data)
        except ValueError as e:
            return {"errore": str(e)}
    else:
        ref_date = get_today()

    # Calcola lunedi e venerdi della settimana
    lunedi = ref_date - timedelta(days=ref_date.weekday())
    venerdi = lunedi + timedelta(days=4)

    dates_to_read = get_date_range(lunedi, venerdi)

    # Raccogli entry per progetto
    progetti = {}  # {progetto: {date: [], entries: []}}
    giorni_con_entry = 0

    for d in dates_to_read:
        file_path = get_file_path(d)
        if not file_path.exists():
            continue

        diary = parse_diary_file(file_path)
        if not diary or not diary.entries:
            continue

        giorni_con_entry += 1

        for entry in diary.entries:
            proj = entry.progetto
            if proj not in progetti:
                progetti[proj] = {"date": [], "entries": []}

            if str(d) not in progetti[proj]["date"]:
                progetti[proj]["date"].append(str(d))

            progetti[proj]["entries"].append({
                "data": str(d),
                "descrizione": entry.descrizione,
                "richiesto_da": entry.richiesto_da,
                "contenuto_preview": entry.contenuto[:300] + "..." if len(entry.contenuto) > 300 else entry.contenuto,
            })

    # Ordina per numero di giorni (progetto piu' presente prima)
    progetti_ordinati = sorted(
        progetti.items(),
        key=lambda x: len(x[1]["date"]),
        reverse=True,
    )

    risultato = []
    for proj, data_proj in progetti_ordinati:
        risultato.append({
            "progetto": proj,
            "giorni": len(data_proj["date"]),
            "date": data_proj["date"],
            "entries": data_proj["entries"],
        })

    return {
        "settimana": {
            "da": str(lunedi),
            "a": str(venerdi),
        },
        "giorni_lavorati": giorni_con_entry,
        "totale_progetti": len(progetti),
        "progetti": risultato,
    }
```

- [ ] **Step 2: Aggiungere il tool in `server.py`**

Aggiungere l'import:
```python
from mcp_cronos.tools.settimana import riassunto_settimana
```

Aggiungere la definizione Tool nell'array TOOLS:
```python
Tool(
    name="cronos_settimana",
    description="""Riassunto settimanale del diario raggruppato per progetto.

Mostra su quanti giorni si e' lavorato per ogni progetto durante la settimana,
con riepilogo delle attivita'. Utile per report settimanali o per capire
la distribuzione del lavoro.

Usa questo tool quando l'utente chiede:
- "Cosa ho fatto questa settimana?"
- "Riassunto settimanale"
- "Su cosa ho lavorato questa settimana?"
- "Report della settimana"

Parametri:
- data (str, optional): Una data nella settimana da analizzare YYYY-MM-DD (default: settimana corrente)

Restituisce: Riassunto per progetto con giorni, date e attivita'.""",
    inputSchema={
        "type": "object",
        "properties": {
            "data": {
                "type": "string",
                "description": "Data nella settimana YYYY-MM-DD (default: corrente)"
            }
        }
    }
),
```

Aggiungere il handler in `call_tool`:
```python
elif name == "cronos_settimana":
    result = riassunto_settimana(
        data=arguments.get("data"),
    )
```

- [ ] **Step 3: Verificare che compili**

Run: `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/tmp uv run python -c "from mcp_cronos.tools.settimana import riassunto_settimana; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos
git add src/mcp_cronos/tools/settimana.py src/mcp_cronos/server.py
git commit -m "feat: aggiungi tool cronos_settimana per riassunto settimanale"
```

---

### Task 8: Nuovo tool `cronos_aggiungi_a_progetto`

**Files:**
- Create: `src/mcp_cronos/tools/aggiungi_progetto.py`
- Modify: `src/mcp_cronos/server.py`

- [ ] **Step 1: Creare `aggiungi_progetto.py`**

```python
"""
Tool per aggiungere contenuto a un'entry di progetto esistente.

Se nel diario di oggi esiste gia' un'entry per lo stesso progetto,
aggiunge una sotto-sezione (H4) invece di creare un'entry nuova.
Se non esiste, crea una nuova entry standard.
"""

import re
from typing import Optional

from mcp_cronos.utils.dates import get_file_path, get_today, parse_date, ensure_directory_exists, get_standup_title
from mcp_cronos.utils.markdown import parse_diary_file
from mcp_cronos.templates import Entry, Riferimento, crea_template_vuoto


def aggiungi_a_progetto(
    progetto: str,
    titolo_fase: str,
    contenuto: str,
    richiesto_da: Optional[str] = None,
    repository: Optional[str] = None,
    branch: Optional[str] = None,
    jira_ticket: Optional[str] = None,
    jira_url: Optional[str] = None,
    gitlab_mr: Optional[str] = None,
    gitlab_mr_url: Optional[str] = None,
    data: Optional[str] = None,
) -> dict:
    """
    Aggiunge contenuto a un'entry di progetto esistente o ne crea una nuova.

    Se esiste gia' un'entry per il progetto specificato, aggiunge una
    sotto-sezione H4. Se non esiste, crea una nuova entry standard.

    Args:
        progetto: Nome del progetto (deve corrispondere esattamente)
        titolo_fase: Titolo della sotto-sezione (es. "Fix bug login", "Deploy v1.2.3")
        contenuto: Contenuto della sotto-sezione
        richiesto_da: Chi ha richiesto il lavoro (opzionale)
        repository: Nome del repository (opzionale)
        branch: Nome del branch (opzionale)
        jira_ticket: Codice ticket Jira (opzionale)
        jira_url: URL del ticket Jira (opzionale)
        gitlab_mr: Numero MR GitLab (opzionale)
        gitlab_mr_url: URL della MR GitLab (opzionale)
        data: Data del file YYYY-MM-DD (default: oggi)

    Returns:
        Dict con risultato operazione
    """
    if data:
        try:
            file_date = parse_date(data)
        except ValueError as e:
            return {"errore": str(e)}
    else:
        file_date = get_today()

    file_path = get_file_path(file_date)
    ensure_directory_exists(file_path)

    # Costruisci riferimenti
    riferimenti_lines = _build_riferimenti_lines(
        repository, branch, jira_ticket, jira_url, gitlab_mr, gitlab_mr_url
    )

    # Se il file non esiste, crea nuova entry
    if not file_path.exists():
        return _crea_nuova_entry(
            file_path, file_date, progetto, titolo_fase, contenuto,
            richiesto_da, riferimenti_lines
        )

    file_content = file_path.read_text(encoding="utf-8")

    # Cerca entry esistente per questo progetto
    # Pattern: ### {progetto} - {descrizione}
    pattern = re.compile(
        rf"^### {re.escape(progetto)}\s*-\s*(.+)$",
        re.MULTILINE,
    )
    match = pattern.search(file_content)

    if match:
        # Progetto trovato: aggiungi sotto-sezione H4
        return _aggiungi_fase(
            file_path, file_content, match, progetto,
            titolo_fase, contenuto, richiesto_da, riferimenti_lines
        )
    else:
        # Progetto non trovato: crea nuova entry
        return _crea_nuova_entry(
            file_path, file_date, progetto, titolo_fase, contenuto,
            richiesto_da, riferimenti_lines
        )


def _build_riferimenti_lines(repository, branch, jira_ticket, jira_url, gitlab_mr, gitlab_mr_url):
    """Costruisce le righe markdown dei riferimenti."""
    lines = []
    if repository:
        lines.append(f"- Repository: {repository}")
    if branch:
        lines.append(f"- Branch: `{branch}`")
    if jira_ticket:
        if jira_url:
            lines.append(f"- Jira: [{jira_ticket}]({jira_url})")
        else:
            lines.append(f"- Jira: {jira_ticket}")
    if gitlab_mr:
        mr_label = f"MR {gitlab_mr}" if not gitlab_mr.startswith("MR") else gitlab_mr
        if gitlab_mr_url:
            lines.append(f"- GitLab MR: [{mr_label}]({gitlab_mr_url})")
        else:
            lines.append(f"- GitLab MR: {mr_label}")
    return lines


def _aggiungi_fase(file_path, file_content, match, progetto, titolo_fase, contenuto, richiesto_da, riferimenti_lines):
    """Aggiunge una sotto-sezione H4 a un'entry esistente."""
    # Trova la fine dell'entry corrente (prossimo ### o ## o ---)
    entry_start = match.start()
    rest = file_content[match.end():]

    # Cerca la fine dell'entry: prossimo ### o ## Bloccanti o ---\n\n###
    end_pattern = re.search(r"\n(?=### |\n## Bloccanti)", rest)
    if end_pattern:
        insert_pos = match.end() + end_pattern.start()
    else:
        # Inserisci prima di ## Bloccanti
        bloccanti_match = re.search(r"\n## Bloccanti", file_content)
        if bloccanti_match:
            insert_pos = bloccanti_match.start()
        else:
            insert_pos = len(file_content)

    # Costruisci la sotto-sezione
    fase_lines = [f"\n\n#### {titolo_fase}\n"]
    if richiesto_da:
        fase_lines.append(f"*-Richiesto da {richiesto_da}-*\n")
    fase_lines.append(contenuto)
    if riferimenti_lines:
        fase_lines.append("\n**Riferimenti:**")
        fase_lines.extend(riferimenti_lines)

    fase_md = "\n".join(fase_lines)

    # Inserisci nel file
    new_content = file_content[:insert_pos] + fase_md + file_content[insert_pos:]
    file_path.write_text(new_content, encoding="utf-8")

    return {
        "successo": True,
        "file": str(file_path),
        "data": str(file_path.stem[:10]),
        "progetto": progetto,
        "fase": titolo_fase,
        "modalita": "aggiunto_a_esistente",
        "messaggio": f"Fase '{titolo_fase}' aggiunta all'entry '{progetto}'"
    }


def _crea_nuova_entry(file_path, file_date, progetto, titolo_fase, contenuto, richiesto_da, riferimenti_lines):
    """Crea una nuova entry con il contenuto come prima fase."""
    # Costruisci il markdown dell'entry
    lines = [f"### {progetto} - {titolo_fase}\n"]
    if richiesto_da:
        lines.append(f"*-Richiesto da {richiesto_da}-*\n")
    lines.append(contenuto)
    if riferimenti_lines:
        lines.append("\n**Riferimenti:**")
        lines.extend(riferimenti_lines)

    entry_md = "\n".join(lines)

    if file_path.exists():
        file_content = file_path.read_text(encoding="utf-8")
    else:
        file_content = crea_template_vuoto(file_date)

    # Inserisci prima di ## Bloccanti
    bloccanti_match = re.search(r"\n## Bloccanti\n", file_content)
    if bloccanti_match:
        insert_pos = bloccanti_match.start()
        new_content = (
            file_content[:insert_pos] +
            "\n" + entry_md + "\n\n---\n" +
            file_content[insert_pos:]
        )
    else:
        new_content = file_content.rstrip() + "\n\n" + entry_md + "\n\n---\n\n## Bloccanti\n\nNessuno\n"

    file_path.write_text(new_content, encoding="utf-8")

    return {
        "successo": True,
        "file": str(file_path),
        "data": str(file_date),
        "progetto": progetto,
        "fase": titolo_fase,
        "modalita": "nuova_entry",
        "messaggio": f"Nuova entry creata per '{progetto}'"
    }
```

- [ ] **Step 2: Aggiungere il tool in `server.py`**

Aggiungere l'import:
```python
from mcp_cronos.tools.aggiungi_progetto import aggiungi_a_progetto
```

Aggiungere la definizione Tool nell'array TOOLS:
```python
Tool(
    name="cronos_aggiungi_a_progetto",
    description="""Aggiunge contenuto a un'entry di progetto esistente nel diario.

Se nel diario di oggi esiste gia' un'entry per il progetto specificato,
aggiunge una sotto-sezione (H4) evitando frammentazione. Se non esiste,
crea una nuova entry standard.

Usa questo tool quando:
- L'utente aggiunge lavoro su un progetto gia' presente nel diario di oggi
- "Aggiungi al progetto X che ho fatto anche Y"
- "Ho continuato su X, aggiungi..."

Per una nuova entry su un progetto nuovo, usa cronos_aggiungi_entry.

Parametri:
- progetto (str, required): Nome esatto del progetto (deve corrispondere all'H3 esistente)
- titolo_fase (str, required): Titolo della sotto-sezione (es. "Fix bug login")
- contenuto (str, required): Contenuto della sotto-sezione
- richiesto_da (str, optional): Chi ha richiesto il lavoro
- repository (str, optional): Nome del repository
- branch (str, optional): Nome del branch
- jira_ticket (str, optional): Codice ticket Jira
- jira_url (str, optional): URL del ticket Jira
- gitlab_mr (str, optional): Numero MR GitLab
- gitlab_mr_url (str, optional): URL della MR GitLab
- data (str, optional): Data YYYY-MM-DD (default: oggi)

Restituisce: Conferma con modalita' (aggiunto_a_esistente o nuova_entry).""",
    inputSchema={
        "type": "object",
        "properties": {
            "progetto": {
                "type": "string",
                "description": "Nome esatto del progetto"
            },
            "titolo_fase": {
                "type": "string",
                "description": "Titolo della sotto-sezione"
            },
            "contenuto": {
                "type": "string",
                "description": "Contenuto della sotto-sezione"
            },
            "richiesto_da": {
                "type": "string",
                "description": "Chi ha richiesto il lavoro (opzionale)"
            },
            "repository": {
                "type": "string",
                "description": "Nome del repository (opzionale)"
            },
            "branch": {
                "type": "string",
                "description": "Nome del branch (opzionale)"
            },
            "jira_ticket": {
                "type": "string",
                "description": "Codice ticket Jira (opzionale)"
            },
            "jira_url": {
                "type": "string",
                "description": "URL del ticket Jira (opzionale)"
            },
            "gitlab_mr": {
                "type": "string",
                "description": "Numero MR GitLab (opzionale)"
            },
            "gitlab_mr_url": {
                "type": "string",
                "description": "URL della MR GitLab (opzionale)"
            },
            "data": {
                "type": "string",
                "description": "Data YYYY-MM-DD (default: oggi)"
            }
        },
        "required": ["progetto", "titolo_fase", "contenuto"]
    }
),
```

Aggiungere il handler in `call_tool`:
```python
elif name == "cronos_aggiungi_a_progetto":
    result = aggiungi_a_progetto(
        progetto=arguments["progetto"],
        titolo_fase=arguments["titolo_fase"],
        contenuto=arguments["contenuto"],
        richiesto_da=arguments.get("richiesto_da"),
        repository=arguments.get("repository"),
        branch=arguments.get("branch"),
        jira_ticket=arguments.get("jira_ticket"),
        jira_url=arguments.get("jira_url"),
        gitlab_mr=arguments.get("gitlab_mr"),
        gitlab_mr_url=arguments.get("gitlab_mr_url"),
        data=arguments.get("data"),
    )
```

- [ ] **Step 3: Verificare che compili**

Run: `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/tmp uv run python -c "from mcp_cronos.tools.aggiungi_progetto import aggiungi_a_progetto; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos
git add src/mcp_cronos/tools/aggiungi_progetto.py src/mcp_cronos/server.py
git commit -m "feat: aggiungi tool cronos_aggiungi_a_progetto per append intelligente"
```

---

### Task 9: Aggiornare `server.py` docstring e pulizia finale

**Files:**
- Modify: `src/mcp_cronos/server.py`

- [ ] **Step 1: Aggiornare il docstring del modulo**

```python
"""
MCP Server per la gestione del diario di lavoro.

Server MCP (Model Context Protocol) che espone tool per:
- Aggiungere entry al diario giornaliero
- Aggiungere contenuto a entry di progetto esistenti
- Leggere entry per data o range
- Generare riassunti discorsivi per lo stand-up
- Cercare testo nelle entry
- Generare riassunti settimanali
- Gestire bloccanti
- Elencare progetti menzionati
- Chiudere la giornata con riassunti e consolidamento

Configurazione:
    Variabile d'ambiente CRONOS_DIARIO_PATH (obbligatoria): path del diario

Utilizzo:
    mcp-cronos                    # Avvia il server
    python -m mcp_cronos.server   # Alternativa
"""
```

- [ ] **Step 2: Verificare import completi e ordinati**

Gli import in `server.py` devono essere:
```python
from mcp_cronos.tools.entries import aggiungi_entry, imposta_bloccanti
from mcp_cronos.tools.reader import leggi_diario, lista_progetti
from mcp_cronos.tools.standup import genera_riassunto_standup
from mcp_cronos.tools.fine_giornata import fine_giornata
from mcp_cronos.tools.consolida import consolida_diario
from mcp_cronos.tools.cerca import cerca_nel_diario
from mcp_cronos.tools.settimana import riassunto_settimana
from mcp_cronos.tools.aggiungi_progetto import aggiungi_a_progetto
```

Verificare che NON ci sia piu' l'import di `genera_slack_domenico`.

- [ ] **Step 3: Test integrazione completo**

Run: `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/Users/mauriziomocci/Documents/workspace/Diario uv run python -c "
from mcp_cronos.server import TOOLS
print(f'Tool registrati: {len(TOOLS)}')
for t in TOOLS:
    print(f'  - {t.name}')
print()
# Verifica che slack sia stato rimosso
names = [t.name for t in TOOLS]
assert 'cronos_genera_slack_domenico' not in names, 'ERROR: slack tool ancora presente!'
assert 'cronos_cerca' in names, 'ERROR: cerca tool mancante!'
assert 'cronos_settimana' in names, 'ERROR: settimana tool mancante!'
assert 'cronos_aggiungi_a_progetto' in names, 'ERROR: aggiungi_a_progetto mancante!'
print('Tutti i check OK')
"`
Expected:
```
Tool registrati: 9
  - cronos_aggiungi_entry
  - cronos_leggi_diario
  - cronos_imposta_bloccanti
  - cronos_riassunto_standup
  - cronos_fine_giornata
  - cronos_consolida_diario
  - cronos_lista_progetti
  - cronos_cerca
  - cronos_settimana
  - cronos_aggiungi_a_progetto
Tutti i check OK
```

- [ ] **Step 4: Commit**

```bash
cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos
git add src/mcp_cronos/server.py
git commit -m "refactor: aggiorna docstring server e pulizia import"
```

---

### Task 10: Verifica end-to-end

- [ ] **Step 1: Test ricerca nel diario reale**

Run: `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/Users/mauriziomocci/Documents/workspace/Diario uv run python -c "
from mcp_cronos.tools.cerca import cerca_nel_diario
r = cerca_nel_diario('Goceano', ultimi_giorni=30)
print(f'Risultati per Goceano: {r[\"totale_risultati\"]}')
for res in r['risultati'][:3]:
    print(f'  {res[\"data\"]}: {res[\"progetto\"]} - {res[\"descrizione\"][:50]}')
"`
Expected: almeno 1 risultato per Goceano

- [ ] **Step 2: Test riassunto settimana**

Run: `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && CRONOS_DIARIO_PATH=/Users/mauriziomocci/Documents/workspace/Diario uv run python -c "
from mcp_cronos.tools.settimana import riassunto_settimana
r = riassunto_settimana()
print(f'Settimana: {r[\"settimana\"][\"da\"]} - {r[\"settimana\"][\"a\"]}')
print(f'Giorni lavorati: {r[\"giorni_lavorati\"]}')
print(f'Progetti: {r[\"totale_progetti\"]}')
"`

- [ ] **Step 3: Test nessun riferimento a Domenico rimasto**

Run: `cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos && grep -ri "domenico" src/mcp_cronos/ || echo "OK: nessun riferimento a Domenico"`
Expected: `OK: nessun riferimento a Domenico`

- [ ] **Step 4: Commit finale se tutto OK**

```bash
cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos
git log --oneline -10
```
