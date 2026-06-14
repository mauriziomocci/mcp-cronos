# Piano di implementazione — Robustezza e allineamento documentazione

> **Per worker agentici:** SUB-SKILL RICHIESTA: usare superpowers:subagent-driven-development (consigliato) o superpowers:executing-plans per eseguire questo piano task per task. Gli step usano la sintassi a checkbox (`- [ ]`) per il tracking.

**Obiettivo:** rendere affidabile la base di `mcp-cronos` correggendo il parsing fragile sui code-fence, localizzando le etichette `Riferimenti`/`Richiesto da` nel sistema i18n con retrocompatibilita' sui diari legacy, e allineando README e CLAUDE.md ai 14 tool e al layout cartella-per-giorno reale.

**Architettura:** server MCP sincrono, Python 3.10+. I tool leggono/scrivono markdown via pathlib. Le etichette di lingua vivono in `LanguagePack` (i18n) e vengono risolte da `load_config()` in un singleton `CronosConfig`. Il parsing del diario e' in `utils/markdown.py`.

**Stack:** Python 3.10+, MCP SDK, dataclasses, pathlib, pytest, ruff.

**Riferimento spec:** `docs/specs/2026-06-14-robustness-doc-sync-design.md`

**Lingua:** documentazione di progetto, codice, commenti, docstring e messaggi di commit in inglese (convenzione progetto). Questo piano e la spec sono in italiano su richiesta dell'autore.

---

## Struttura dei file toccati

- `tests/test_markdown.py` (modifica): nuovi test per parsing fenced e per localizzazione/round-trip etichette.
- `tests/test_i18n.py` (modifica): aggiornare `REQUIRED_SECTION_KEYS` e i valori delle nuove etichette.
- `src/mcp_cronos/i18n.py` (modifica): aggiungere `references` e `requested_by` a `sections` in entrambi i pacchetti.
- `src/mcp_cronos/config.py` (modifica): esporre `section_references` e `section_requested_by` su `CronosConfig` e risolverle in `load_config()`.
- `src/mcp_cronos/utils/markdown.py` (modifica): render con etichette configurate; parser che accetta etichetta configurata + default italiano legacy; eventuale fence-awareness.
- `src/mcp_cronos/templates.py` (modifica): `Entry.to_markdown` usa le etichette configurate.
- `src/mcp_cronos/tools/aggiungi_progetto.py` (modifica): helper di build usano le etichette configurate.
- `README.md` (modifica): tre tool mancanti, parametro `tipo` di `cerca`, layout cartella-per-giorno.
- `CLAUDE.md` (modifica): conteggio tool 11 -> 14, albero architettura, scope commit, workflow fine giornata.

---

## Fase 1 — Parsing consapevole dei code-fence (test-first)

### Task 1: Test che fotografa il parsing di una entry con code-fence

**Files:**
- Test: `tests/test_markdown.py`

- [ ] **Step 1: Scrivere il test che fallisce (o passa)**

Aggiungere in coda a `tests/test_markdown.py`:

```python
def test_parse_entries_ignores_headings_inside_code_fence():
    """A fenced code block containing a line starting with '### ' or a '---'
    line must not be parsed as a new entry or as an entry terminator.

    Documents the parser behaviour on fenced content. If this fails, the
    parser is fence-fragile and Task 2 applies.
    """
    from mcp_cronos.utils.markdown import parse_entries

    content = (
        "### MCP Cronos - Refactor parser\n\n"
        "Intro paragraph.\n\n"
        "```bash\n"
        "### this is a shell comment, not a heading\n"
        "echo hello\n"
        "---\n"
        "echo world\n"
        "```\n\n"
        "Closing paragraph.\n"
    )

    entries = parse_entries(content)

    assert len(entries) == 1
    assert entries[0].progetto == "MCP Cronos"
    assert entries[0].descrizione == "Refactor parser"
    assert "echo hello" in entries[0].contenuto
    assert "echo world" in entries[0].contenuto
    assert "Closing paragraph." in entries[0].contenuto
```

- [ ] **Step 2: Eseguire il test e registrare l'esito**

Run: `uv run pytest tests/test_markdown.py::test_parse_entries_ignores_headings_inside_code_fence -v`

Due esiti possibili:
- **PASS**: la fragilita' non esiste in pratica. Aggiungere sopra il test il commento `# Parser already robust to fenced content as of 2026-06-14; kept as regression guard.`, committare, e SALTARE il Task 2.
- **FAIL**: il parser e' fence-fragile. Procedere al Task 2.

- [ ] **Step 3: Commit del test (qualunque esito)**

```bash
git add tests/test_markdown.py
git commit -m "test(markdown): add fenced-code parsing guard

CHANGE: Adds a regression test asserting that lines starting with '### '
or '---' inside a fenced code block are not parsed as entry boundaries."
```

### Task 2: Fence-awareness in parse_entries (SOLO se Task 1 fallisce)

**Files:**
- Modify: `src/mcp_cronos/utils/markdown.py`
- Test: `tests/test_markdown.py`

- [ ] **Step 1: Confermare il fallimento**

Run: `uv run pytest tests/test_markdown.py::test_parse_entries_ignores_headings_inside_code_fence -v`
Atteso: FAIL (es. `len(entries) != 1`).

- [ ] **Step 2: Rendere lo split fence-aware**

In `src/mcp_cronos/utils/markdown.py`, sostituire la riga di split nella funzione `parse_entries`:

```python
    # Split per H3 (###)
    parts = re.split(r"\n(?=### )", content)
```

con una segmentazione che ignora i marker dentro i fence:

```python
    # Split per H3 (###) ignorando le righe dentro blocchi di codice fenced.
    # Un fence (``` o ~~~) puo' contenere righe '### ...' o '---' che NON sono
    # confini di entry: una segmentazione regex naive le tratterebbe come tali.
    parts = _split_entries_respecting_fences(content)
```

E aggiungere la helper sopra `parse_entries`:

```python
def _split_entries_respecting_fences(content: str) -> list[str]:
    """Split content into entry chunks at top-level '### ' headings only.

    Lines inside fenced code blocks (delimited by ``` or ~~~) are treated as
    opaque: a '### ' or '---' line inside a fence does not start or end an
    entry. This prevents shell comments or diff markers in code samples from
    being misread as diary structure.
    """
    parts: list[str] = []
    current: list[str] = []
    in_fence = False
    fence_marker = ""

    for line in content.split("\n"):
        stripped = line.lstrip()
        is_fence_line = stripped.startswith("```") or stripped.startswith("~~~")
        if is_fence_line:
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""

        if not in_fence and line.startswith("### ") and current:
            parts.append("\n".join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        parts.append("\n".join(current))
    return parts
```

- [ ] **Step 3: Verificare che il terminatore `---` non spezzi dentro i fence**

Nel corpo di `parse_entries`, la rimozione del separatore finale e' gia' ancorata alla fine del chunk (`if contenuto.endswith("---")`), quindi un `---` interno al fence non viene toccato. Nessuna modifica ulteriore richiesta qui. Confermarlo rileggendo le righe che fanno `contenuto.endswith("---")`.

- [ ] **Step 4: Eseguire il test mirato**

Run: `uv run pytest tests/test_markdown.py::test_parse_entries_ignores_headings_inside_code_fence -v`
Atteso: PASS.

- [ ] **Step 5: Eseguire l'intera suite (no regressioni)**

Run: `uv run pytest -q`
Atteso: tutti i test verdi.

- [ ] **Step 6: Commit**

```bash
git add src/mcp_cronos/utils/markdown.py
git commit -m "fix(markdown): make entry split fence-aware

CHANGE: parse_entries now segments on top-level '### ' headings only,
treating fenced code blocks as opaque so that '### ' or '---' lines inside
code samples are no longer misread as entry boundaries."
```

---

## Fase 2 — Localizzazione i18n delle etichette

### Task 3: Aggiungere le etichette ai LanguagePack e aggiornarne i test

**Files:**
- Modify: `src/mcp_cronos/i18n.py`
- Test: `tests/test_i18n.py`

- [ ] **Step 1: Aggiornare i test i18n (falliscono prima del fix)**

In `tests/test_i18n.py`, riga 14, sostituire:

```python
REQUIRED_SECTION_KEYS = {"entries", "blockers", "day_summary", "tech_summary", "standup_message"}
```

con:

```python
REQUIRED_SECTION_KEYS = {
    "entries", "blockers", "day_summary", "tech_summary", "standup_message",
    "references", "requested_by",
}
```

Aggiungere a `TestItalianPack.test_sections_values`:

```python
        assert self.pack.sections["references"] == "Riferimenti"
        assert self.pack.sections["requested_by"] == "Richiesto da"
```

Aggiungere a `TestEnglishPack.test_sections_values`:

```python
        assert self.pack.sections["references"] == "References"
        assert self.pack.sections["requested_by"] == "Requested by"
```

- [ ] **Step 2: Eseguire i test e verificarne il fallimento**

Run: `uv run pytest tests/test_i18n.py -v`
Atteso: FAIL su `test_sections_keys` e `test_sections_values` (chiavi mancanti).

- [ ] **Step 3: Aggiungere le chiavi ai due pacchetti**

In `src/mcp_cronos/i18n.py`, nel pacchetto `_IT`, dentro `sections={...}` aggiungere:

```python
        "references": "Riferimenti",
        "requested_by": "Richiesto da",
```

Nel pacchetto `_EN`, dentro `sections={...}` aggiungere:

```python
        "references": "References",
        "requested_by": "Requested by",
```

Aggiornare il commento delle chiavi documentate (riga ~36):

```python
    # sections keys: entries, blockers, day_summary, tech_summary,
    #                standup_message, references, requested_by
```

- [ ] **Step 4: Eseguire i test i18n**

Run: `uv run pytest tests/test_i18n.py -v`
Atteso: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_cronos/i18n.py tests/test_i18n.py
git commit -m "feat(i18n): add references and requested_by section labels

CHANGE: Adds localised 'references' and 'requested_by' labels to the Italian
and English language packs, with tests covering both languages."
```

### Task 4: Esporre le etichette su CronosConfig

**Files:**
- Modify: `src/mcp_cronos/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Scrivere il test che fallisce**

Aggiungere in coda a `tests/test_config.py`:

```python
def test_config_exposes_reference_labels_it(tmp_diario, config_toml_it):
    from mcp_cronos.config import load_config

    config = load_config()
    assert config.section_references == "Riferimenti"
    assert config.section_requested_by == "Richiesto da"


def test_config_exposes_reference_labels_en(tmp_diario, config_toml_en):
    from mcp_cronos.config import load_config

    config = load_config()
    assert config.section_references == "References"
    assert config.section_requested_by == "Requested by"
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `uv run pytest tests/test_config.py -k reference_labels -v`
Atteso: FAIL (`CronosConfig` non ha `section_references`).

- [ ] **Step 3: Aggiungere i campi al dataclass**

In `src/mcp_cronos/config.py`, nella dataclass `CronosConfig`, dopo `section_standup_message: str` aggiungere:

```python
    section_references: str
    section_requested_by: str
```

- [ ] **Step 4: Risolvere le etichette in load_config**

In `load_config()`, dopo il blocco che calcola `section_standup_message` (riga ~197), aggiungere:

```python
    section_references = user_sections.get("references", pack.sections["references"])
    section_requested_by = user_sections.get("requested_by", pack.sections["requested_by"])
```

E nel costruttore `_config = CronosConfig(...)` aggiungere i due argomenti:

```python
        section_references=section_references,
        section_requested_by=section_requested_by,
```

- [ ] **Step 5: Eseguire i test**

Run: `uv run pytest tests/test_config.py -k reference_labels -v`
Atteso: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/mcp_cronos/config.py tests/test_config.py
git commit -m "feat(config): expose references and requested_by labels

CHANGE: CronosConfig now carries section_references and section_requested_by,
resolved from user overrides or language-pack defaults like the other section
labels."
```

### Task 5: Generazione con etichette configurate

**Files:**
- Modify: `src/mcp_cronos/templates.py`
- Modify: `src/mcp_cronos/utils/markdown.py`
- Modify: `src/mcp_cronos/tools/aggiungi_progetto.py`
- Test: `tests/test_markdown.py`

- [ ] **Step 1: Scrivere il test di generazione EN che fallisce**

Aggiungere in coda a `tests/test_markdown.py`:

```python
def test_render_entry_uses_configured_labels_en(tmp_diario, config_toml_en):
    from mcp_cronos.utils.markdown import DiaryEntry, render_entry

    entry = DiaryEntry(
        progetto="MCP Cronos",
        descrizione="Localise labels",
        contenuto="Body text.",
        richiesto_da="Marco",
        riferimenti={"repository": "mcp-cronos"},
    )
    rendered = render_entry(entry)

    assert "*-Requested by Marco-*" in rendered
    assert "**References:**" in rendered
    assert "Riferimenti" not in rendered
    assert "Richiesto da" not in rendered
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `uv run pytest tests/test_markdown.py::test_render_entry_uses_configured_labels_en -v`
Atteso: FAIL (render usa "Riferimenti"/"Richiesto da" hardcoded).

- [ ] **Step 3: Localizzare il render in markdown.py**

In `src/mcp_cronos/utils/markdown.py`, dentro `render_entry`, sostituire il blocco "Richiesto da" (righe ~268-270):

```python
    # Richiesto da (opzionale)
    if entry.richiesto_da:
        lines.append(f"*-Richiesto da {entry.richiesto_da}-*")
        lines.append("")
```

con:

```python
    # Requested-by line (optional), label localised via config.
    if entry.richiesto_da:
        lines.append(f"*-{config.section_requested_by} {entry.richiesto_da}-*")
        lines.append("")
```

e il blocco "Riferimenti" (righe ~275-280):

```python
    # Riferimenti (se non gia' presenti nel contenuto)
    if entry.riferimenti and "**Riferimenti:**" not in entry.contenuto:
        lines.append("")
        lines.append("**Riferimenti:**")
        for key, value in entry.riferimenti.items():
            lines.append(f"- {key.title()}: {value}")
```

con:

```python
    # References block (skip if already present in content, in any accepted label).
    if entry.riferimenti and not _content_has_references(entry.contenuto):
        lines.append("")
        lines.append(f"**{config.section_references}:**")
        for key, value in entry.riferimenti.items():
            lines.append(f"- {key.title()}: {value}")
```

`render_entry` deve avere accesso a `config`: in cima alla funzione aggiungere `config = load_config()` (subito dopo la docstring, prima di `lines = []`).

- [ ] **Step 4: Localizzare templates.py**

In `src/mcp_cronos/templates.py`, dentro `Entry.to_markdown`, all'inizio del metodo aggiungere:

```python
        config = load_config()
```

Sostituire il blocco "Richiesto da" (righe ~68-70):

```python
        # Richiesto da (opzionale)
        if self.richiesto_da:
            lines.append(f"*-Richiesto da {self.richiesto_da}-*")
            lines.append("")
```

con:

```python
        # Requested-by line (optional), label localised via config.
        if self.richiesto_da:
            lines.append(f"*-{config.section_requested_by} {self.richiesto_da}-*")
            lines.append("")
```

E la riga del blocco riferimenti (riga ~84):

```python
            lines.append("**Riferimenti:**")
```

con:

```python
            lines.append(f"**{config.section_references}:**")
```

(`load_config` e' gia' importato in `templates.py`.)

- [ ] **Step 5: Localizzare aggiungi_progetto.py**

In `src/mcp_cronos/tools/aggiungi_progetto.py`, in `_aggiungi_fase` (che gia' fa `config = load_config()` alla riga ~131), sostituire le righe ~147 e ~150:

```python
    if richiesto_da:
        fase_lines.append(f"*-Richiesto da {richiesto_da}-*\n")
    fase_lines.append(contenuto)
    if riferimenti_lines:
        fase_lines.append("\n**Riferimenti:**")
```

con:

```python
    if richiesto_da:
        fase_lines.append(f"*-{config.section_requested_by} {richiesto_da}-*\n")
    fase_lines.append(contenuto)
    if riferimenti_lines:
        fase_lines.append(f"\n**{config.section_references}:**")
```

In `_crea_nuova_entry` aggiungere `config = load_config()` come prima riga del corpo (prima di `lines = [...]`), poi sostituire le righe ~175 e ~178:

```python
    if richiesto_da:
        lines.append(f"*-Richiesto da {richiesto_da}-*\n")
    lines.append(contenuto)
    if riferimenti_lines:
        lines.append("\n**Riferimenti:**")
```

con:

```python
    if richiesto_da:
        lines.append(f"*-{config.section_requested_by} {richiesto_da}-*\n")
    lines.append(contenuto)
    if riferimenti_lines:
        lines.append(f"\n**{config.section_references}:**")
```

- [ ] **Step 6: Aggiungere la helper `_content_has_references` in markdown.py**

Sopra `render_entry`, aggiungere:

```python
# Italian default labels kept for backward compatibility: every diary written
# before label localisation used these literals, regardless of language.
_LEGACY_REFERENCES_LABEL = "Riferimenti"
_LEGACY_REQUESTED_BY_LABEL = "Richiesto da"


def _accepted_reference_labels() -> set[str]:
    """Reference labels the parser accepts: configured value + Italian legacy."""
    config = load_config()
    return {config.section_references, _LEGACY_REFERENCES_LABEL}


def _content_has_references(content: str) -> bool:
    """True if content already contains a references block in any accepted label."""
    return any(f"**{label}:**" in content for label in _accepted_reference_labels())
```

- [ ] **Step 7: Eseguire i test mirati e la suite**

Run: `uv run pytest tests/test_markdown.py::test_render_entry_uses_configured_labels_en -v`
Atteso: PASS.

Run: `uv run pytest -q`
Atteso: tutti verdi.

- [ ] **Step 8: Commit**

```bash
git add src/mcp_cronos/templates.py src/mcp_cronos/utils/markdown.py src/mcp_cronos/tools/aggiungi_progetto.py tests/test_markdown.py
git commit -m "feat(markdown): render references and requested-by with configured labels

CHANGE: Entry rendering in markdown.py, templates.py and aggiungi_progetto.py
now uses config.section_references / section_requested_by instead of hardcoded
Italian literals. Adds _content_has_references helper that recognises the
configured label and the Italian legacy label."
```

### Task 6: Parsing con etichetta configurata + fallback legacy italiano

**Files:**
- Modify: `src/mcp_cronos/utils/markdown.py`
- Test: `tests/test_markdown.py`

- [ ] **Step 1: Scrivere il test di retrocompatibilita' che fallisce**

Aggiungere in coda a `tests/test_markdown.py`:

```python
def test_parse_legacy_italian_references_under_english_config(tmp_diario, config_toml_en):
    """A diary written with Italian labels must still parse its references and
    requester even when the active language is English (no data migration)."""
    from mcp_cronos.utils.markdown import parse_entries

    content = (
        "### SmarTicket - Fix login\n\n"
        "*-Richiesto da Marco-*\n\n"
        "Fixed timeout.\n\n"
        "**Riferimenti:**\n"
        "- Repository: smarticket-backend\n"
        "- Branch: `fix/login`\n"
    )
    entries = parse_entries(content)

    assert len(entries) == 1
    assert entries[0].richiesto_da == "Marco"
    assert entries[0].riferimenti is not None
    assert entries[0].riferimenti.get("repository") == "smarticket-backend"


def test_parse_english_references_under_english_config(tmp_diario, config_toml_en):
    """References and requester written with English labels must parse under en."""
    from mcp_cronos.utils.markdown import parse_entries

    content = (
        "### SmarTicket - Fix login\n\n"
        "*-Requested by Marco-*\n\n"
        "Fixed timeout.\n\n"
        "**References:**\n"
        "- Repository: smarticket-backend\n"
    )
    entries = parse_entries(content)

    assert len(entries) == 1
    assert entries[0].richiesto_da == "Marco"
    assert entries[0].riferimenti is not None
    assert entries[0].riferimenti.get("repository") == "smarticket-backend"
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `uv run pytest tests/test_markdown.py -k references_under_english -v`
Atteso: il caso English FALLISCE (parser cerca solo "Riferimenti"/"Richiesto da"); il caso legacy italiano potrebbe gia' passare.

- [ ] **Step 3: Rendere `extract_references` multi-label**

In `src/mcp_cronos/utils/markdown.py`, sostituire l'inizio di `extract_references` (righe ~225-233):

```python
    if "**Riferimenti:**" not in content:
        return None

    refs = {}
    in_refs = False

    for line in content.split("\n"):
        if "**Riferimenti:**" in line:
            in_refs = True
            continue
```

con:

```python
    ref_headers = {f"**{label}:**" for label in _accepted_reference_labels()}
    if not any(h in content for h in ref_headers):
        return None

    refs = {}
    in_refs = False

    for line in content.split("\n"):
        if any(h in line for h in ref_headers):
            in_refs = True
            continue
```

- [ ] **Step 4: Rendere la regex "Richiesto da" multi-label**

Sempre in `markdown.py`, in `parse_entries`, sostituire il blocco di ricerca del richiedente (righe ~169-174):

```python
        # Cerca "Richiesto da"
        richiesto_da = None
        for line in contenuto_lines:
            match = re.match(r"\*-Richiesto da (.+)-\*", line.strip())
            if match:
                richiesto_da = match.group(1)
                break
```

con:

```python
        # Match the requester line for the configured label or the Italian
        # legacy label, so diaries written before localisation still parse.
        config = load_config()
        labels = {config.section_requested_by, _LEGACY_REQUESTED_BY_LABEL}
        label_alt = "|".join(re.escape(lbl) for lbl in labels)
        requested_by_re = re.compile(rf"\*-(?:{label_alt}) (.+)-\*")
        richiesto_da = None
        for line in contenuto_lines:
            match = requested_by_re.match(line.strip())
            if match:
                richiesto_da = match.group(1)
                break
```

- [ ] **Step 5: Eseguire i test mirati e la suite**

Run: `uv run pytest tests/test_markdown.py -k references_under_english -v`
Atteso: entrambi PASS.

Run: `uv run pytest -q`
Atteso: tutti verdi.

- [ ] **Step 6: Commit**

```bash
git add src/mcp_cronos/utils/markdown.py tests/test_markdown.py
git commit -m "fix(markdown): parse references and requester for configured and legacy labels

CHANGE: extract_references and the requester regex now accept the configured
label and the Italian legacy label, so diaries written before localisation
remain parseable after a language switch. No data migration required."
```

---

## Fase 3 — Allineamento documentazione

### Task 7: Aggiornare CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Correggere il conteggio dei tool**

In `CLAUDE.md`:
- Riga ~36 (`server.py ... (11 tools)`): cambiare `(11 tools)` in `(14 tools)`.
- Riga ~228 (`Tool dispatch is manual ... for 11 tools`): cambiare `for 11 tools` in `for 14 tools`.

- [ ] **Step 2: Aggiungere i moduli mancanti all'albero architettura**

Nella sezione `tools/` dell'albero (righe ~42-51), dopo `aggiungi_progetto.py`, aggiungere:

```
    leggi_todo.py         # cronos_leggi_todo (read todo.md for a date)
    lista_mese.py         # cronos_lista_mese (month dashboard of diary artifacts)
    prepara_domani.py     # cronos_prepara_domani (set up next working day folder)
```

- [ ] **Step 3: Estendere gli scope di commit**

Nella riga "Scope: module name ..." (riga ~154), aggiungere alla lista: `leggi_todo`, `lista_mese`, `prepara_domani`, `i18n`, `template_loader`.

- [ ] **Step 4: Citare prepara_domani nel workflow fine giornata**

Nella sezione "End-of-Day Workflow" (righe ~214-222), aggiungere dopo il punto 3:

```
4. Optionally call `cronos_prepara_domani` to create the next working day's
   folder with a `todo.md` and an empty `raw.md` skeleton, carrying over open
   points from the day just closed.
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): sync architecture and tool count with code

CHANGE: Corrects the tool count from 11 to 14, adds leggi_todo, lista_mese and
prepara_domani to the architecture tree and commit-scope list, and documents
prepara_domani in the end-of-day workflow."
```

### Task 8: Aggiornare README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Aggiungere le feature mancanti agli elenchi**

Nelle liste "Features" (sezione English, righe ~13-27) e "Funzionalita'" (sezione Italiano, righe ~348-362), aggiungere tre voci coerenti con lo stile esistente, ad es. (English):

```
- **Read todo**: Read the `todo.md` for a given day (what was planned)
- **Month dashboard**: At-a-glance month view of which artifacts exist per day
- **Prepare next day**: Create the next working day's folder with todo and raw skeleton
```

e gli equivalenti italiani nella sezione "Funzionalita'".

- [ ] **Step 2: Documentare il parametro `tipo` di `cronos_cerca`**

Nella sezione `#### cronos_cerca` (English, righe ~223-235 e Italiano ~558-570), aggiungere ai parametri opzionali:

```
- `tipo` (list[str]): Sources to search — `"raw"`, `"todo"`, `"chiusura"`. Default: all three.
```

e aggiornare la frase introduttiva da "Search diary entries" a "Search across diary sources (raw entries, todo files, end-of-day files)".

- [ ] **Step 3: Aggiungere le tre sezioni tool mancanti**

Dopo `#### cronos_scrivi_fine_giornata` (in entrambe le lingue), aggiungere tre sottosezioni `#### cronos_leggi_todo`, `#### cronos_lista_mese`, `#### cronos_prepara_domani`, ricalcando lo schema delle altre (descrizione, parametri obbligatori/opzionali, Returns). Usare le descrizioni e gli inputSchema gia' presenti in `server.py` (`TOOLS`) come fonte autorevole per parametri e default.

- [ ] **Step 4: Aggiornare la sezione "Diary Format" / "Formato Diario"**

Sostituire la descrizione del layout a file singolo con il layout cartella-per-giorno, conservando una nota sul legacy. Struttura da documentare (entrambe le lingue):

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

Aggiungere una frase: i giorni con file legacy continuano a usare il file singolo (nessuna migrazione); i nuovi giorni usano la cartella.

- [ ] **Step 5: Verifica incrociata server.py <-> README**

Run: `uv run python -c "from mcp_cronos.server import TOOLS; print('\n'.join(sorted(t.name for t in TOOLS)))"`

Confermare a vista che ognuno dei 14 nomi stampati abbia una sezione `####` corrispondente nel README (in entrambe le lingue).

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs(readme): document missing tools, cerca tipo param, folder layout

CHANGE: Adds cronos_leggi_todo, cronos_lista_mese and cronos_prepara_domani to
both language sections, documents the cerca 'tipo' parameter, and replaces the
single-file diary layout description with the current per-day folder layout
(legacy single-file noted)."
```

---

## Chiusura della Fase A

- [ ] **Step finale: suite completa verde + lint**

Run: `uv run pytest -q`
Atteso: tutti i test verdi, zero fallimenti.

Run: `uv run ruff check src/mcp_cronos/ && uv run ruff format --check src/mcp_cronos/`
Atteso: nessun problema.

A questo punto il branch `feature/robustness-doc-sync` contiene la spec, il piano e l'implementazione completa di A. Il merge su `master` e il push restano decisioni dell'utente (mai push automatico).

---

## Note di esecuzione

- Ordine obbligatorio: Fase 1 (test fence) prima di tutto, perche' l'esito decide se il Task 2 esiste. Poi Fase 2 (i18n), poi Fase 3 (doc), cosi' la documentazione descrive lo stato gia' corretto.
- Ogni task e' indipendente e committabile da solo; nessun task dipende da codice introdotto in un task successivo.
- Se durante l'esecuzione emerge un caso non previsto (es. il parser e' fragile in un modo diverso da quello ipotizzato), fermarsi ed escalare: rivedere la spec prima di inventare una soluzione.
