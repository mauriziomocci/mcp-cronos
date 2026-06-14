# Piano di implementazione — Comodita' workflow giornaliero (C2-C4)

> **Per worker agentici:** SUB-SKILL: superpowers:subagent-driven-development. Step a checkbox.

**Obiettivo:** tre comodita' del workflow giornaliero: auto-rilevamento git di repository/branch (C2), `paragrafo_intro` opzionale (C3), chiusura serale che prepara anche il domani in un comando (C4).

**Architettura:** nuovo modulo `utils/gitinfo.py` per il rilevamento git; integrazione nei tool di entry; `paragrafo_intro` opzionale con render che salta l'intro vuoto; `scrivi_fine_giornata` esteso con `contenuto_todo` opzionale che inoltra a `prepara_domani`.

**Stack:** Python 3.10+, subprocess (git), pytest, ruff.

**Riferimento spec:** `docs/specs/2026-06-14-daily-workflow-conveniences-design.md`

**Lingua:** codice/commit in inglese; piano/spec in italiano.

---

## Task 1: C2 — modulo gitinfo

**Files:** Create `src/mcp_cronos/utils/gitinfo.py`; Test `tests/test_gitinfo.py` (nuovo).

- [ ] **Step 1: test che fallisce**

Creare `tests/test_gitinfo.py`:

```python
"""Tests for mcp_cronos.utils.gitinfo (git repository/branch detection)."""

import subprocess


def _init_repo(path, branch="feature-x"):
    subprocess.run(["git", "init", "-b", branch, str(path)], check=True, capture_output=True)
    (path / "file.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-m", "init"],
        check=True, capture_output=True,
    )


def test_detect_git_info_returns_repo_and_branch(tmp_path):
    from mcp_cronos.utils.gitinfo import detect_git_info

    repo = tmp_path / "myrepo"
    repo.mkdir()
    _init_repo(repo, branch="feature-x")

    repository, branch = detect_git_info(str(repo))
    assert repository == "myrepo"
    assert branch == "feature-x"


def test_detect_git_info_non_git_dir_returns_none(tmp_path):
    from mcp_cronos.utils.gitinfo import detect_git_info

    plain = tmp_path / "plain"
    plain.mkdir()
    repository, branch = detect_git_info(str(plain))
    assert repository is None
    assert branch is None
```

Run: `uv run pytest tests/test_gitinfo.py -v` → FAIL (module missing).

- [ ] **Step 2: creare il modulo**

`src/mcp_cronos/utils/gitinfo.py`:

```python
"""Best-effort git repository/branch detection for diary entries.

Reads the repository name and current branch from a git working directory so
entry tools can fill the `repository` and `branch` fields automatically. The
target directory is an explicit path or the server process working directory;
any failure (not a git repo, git missing) yields (None, None) without raising,
so detection never blocks entry creation.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional


def _run_git(args: list[str], cwd: str) -> Optional[str]:
    """Run a git command in cwd and return stripped stdout, or None on any failure."""
    try:
        result = subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def detect_git_info(working_dir: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """Detect (repository_name, branch) from a git working directory.

    Args:
        working_dir: Directory to inspect; defaults to the current working
            directory of the server process.

    Returns:
        (repository_name, branch). repository_name is the basename of the repo
        top-level. Either element is None when it cannot be determined.
    """
    cwd = working_dir or os.getcwd()
    toplevel = _run_git(["rev-parse", "--show-toplevel"], cwd)
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    repository = Path(toplevel).name if toplevel else None
    return repository, branch
```

- [ ] **Step 3: verificare**

Run: `uv run pytest tests/test_gitinfo.py -v` → PASS.
Run: `uv run pytest -q` → verde. Run: `uv run ruff check src/mcp_cronos/utils/gitinfo.py tests/test_gitinfo.py` → pulito.

- [ ] **Step 4: commit**

```bash
git add src/mcp_cronos/utils/gitinfo.py tests/test_gitinfo.py
git commit -m "feat(gitinfo): add best-effort git repo and branch detection

CHANGE: New utils/gitinfo.py with detect_git_info reading repository name and
current branch from a git working directory (explicit path or process cwd),
returning (None, None) on any failure without raising."
```

---

## Task 2: C2 — integrazione nei tool di entry

**Files:** Modify `src/mcp_cronos/tools/entries.py`, `src/mcp_cronos/tools/aggiungi_progetto.py`, `src/mcp_cronos/server.py`; Test `tests/test_entries.py`, `tests/test_aggiungi_progetto.py`.

- [ ] **Step 1: test che fallisce (entries)**

Aggiungere a `tests/test_entries.py` (riusare l'helper `_init_repo` definendolo nel file, o importarlo; per semplicita' ridefinirlo inline):

```python
import subprocess


def _init_repo_e(path, branch="dev-branch"):
    subprocess.run(["git", "init", "-b", branch, str(path)], check=True, capture_output=True)
    (path / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-m", "i"],
        check=True, capture_output=True,
    )


def test_aggiungi_entry_autodetects_git(tmp_diario, tmp_path):
    from mcp_cronos.tools.entries import aggiungi_entry

    repo = tmp_path / "autorepo"
    repo.mkdir()
    _init_repo_e(repo, branch="dev-branch")

    result = aggiungi_entry(
        progetto="P", descrizione="D", paragrafo_intro="intro",
        data="2026-04-09", working_dir=str(repo),
    )
    from pathlib import Path
    content = Path(result["file"]).read_text(encoding="utf-8")
    assert "autorepo" in content
    assert "dev-branch" in content


def test_aggiungi_entry_explicit_repository_wins(tmp_diario, tmp_path):
    from mcp_cronos.tools.entries import aggiungi_entry

    repo = tmp_path / "autorepo"
    repo.mkdir()
    _init_repo_e(repo, branch="dev-branch")

    result = aggiungi_entry(
        progetto="P", descrizione="D", paragrafo_intro="intro", data="2026-04-09",
        repository="explicit-repo", working_dir=str(repo),
    )
    from pathlib import Path
    content = Path(result["file"]).read_text(encoding="utf-8")
    assert "explicit-repo" in content
    assert "autorepo" not in content
```

Run: `uv run pytest tests/test_entries.py -k autodetect or explicit_repository -v` → FAIL (param `working_dir` assente).

- [ ] **Step 2: integrare in aggiungi_entry (entries.py)**

Aggiungere l'import:
```python
from mcp_cronos.utils.gitinfo import detect_git_info
```
Aggiungere `working_dir: Optional[str] = None` alla firma di `aggiungi_entry` (dopo `data`). Aggiungere al docstring Args una riga per `working_dir`. Subito dopo la risoluzione della data (dopo il blocco `if data: ... else: file_date = get_today()`), aggiungere:
```python
    # Auto-detect repository/branch from git when not provided explicitly.
    if repository is None or branch is None:
        det_repo, det_branch = detect_git_info(working_dir)
        repository = repository or det_repo
        branch = branch or det_branch
```
Il resto (costruzione `riferimenti`) resta invariato e usa i valori ora eventualmente riempiti.

- [ ] **Step 3: integrare in aggiungi_a_progetto (aggiungi_progetto.py)**

Aggiungere l'import `from mcp_cronos.utils.gitinfo import detect_git_info`. Aggiungere `working_dir: Optional[str] = None` alla firma di `aggiungi_a_progetto` (dopo `data`). Subito dopo la risoluzione della data, prima di `_build_riferimenti_lines`, aggiungere lo stesso blocco di riempimento:
```python
    if repository is None or branch is None:
        det_repo, det_branch = detect_git_info(working_dir)
        repository = repository or det_repo
        branch = branch or det_branch
```

- [ ] **Step 4: server.py — schema + dispatch per entrambi i tool**

In `cronos_aggiungi_entry` e `cronos_aggiungi_a_progetto`: aggiungere a `inputSchema["properties"]`:
```python
                "working_dir": {
                    "type": "string",
                    "description": (
                        "Directory di lavoro git da cui rilevare repository e branch "
                        "se non forniti (opzionale)"
                    ),
                },
```
e una riga nella descrizione testuale. Nel dispatch di entrambi, aggiungere:
```python
                working_dir=arguments.get("working_dir"),
```

- [ ] **Step 5: aggiungere un test analogo per aggiungi_a_progetto**

In `tests/test_aggiungi_progetto.py`, aggiungere un test `test_aggiungi_a_progetto_autodetects_git(tmp_diario, tmp_path)` che crea un repo git, chiama `aggiungi_a_progetto(progetto="P", titolo_fase="F", contenuto="C", data="2026-04-09", working_dir=str(repo))` e verifica che il file contenga il basename del repo e il branch. (Definire un helper `_init_repo` inline come sopra.)

- [ ] **Step 6: verificare**

Run: `uv run pytest tests/test_entries.py tests/test_aggiungi_progetto.py -v` → verdi.
Run: `uv run pytest -q` → verde. `uv run ruff check ...` sui file toccati → pulito.

- [ ] **Step 7: commit**

```bash
git add src/mcp_cronos/tools/entries.py src/mcp_cronos/tools/aggiungi_progetto.py src/mcp_cronos/server.py tests/test_entries.py tests/test_aggiungi_progetto.py
git commit -m "feat(entries): auto-fill repository and branch from git

CHANGE: aggiungi_entry and aggiungi_a_progetto accept an optional working_dir
and fill repository/branch from git detection when not provided; explicit values
always win. Wires working_dir into the server tool schemas and dispatch."
```

---

## Task 3: C3 — paragrafo_intro opzionale

**Files:** Modify `src/mcp_cronos/tools/entries.py`, `src/mcp_cronos/templates.py`, `src/mcp_cronos/server.py`; Test `tests/test_entries.py`, `tests/test_templates.py`.

- [ ] **Step 1: test che fallisce**

Aggiungere a `tests/test_entries.py`:
```python
def test_aggiungi_entry_without_intro(tmp_diario):
    from pathlib import Path

    from mcp_cronos.tools.entries import aggiungi_entry

    result = aggiungi_entry(progetto="P", descrizione="D", data="2026-04-09")
    content = Path(result["file"]).read_text(encoding="utf-8")
    assert "### P - D" in content
    # No spurious empty intro line: the header is not followed by two blank lines
    # then another blank (rough guard: the rendered entry has no triple newline).
    assert "\n\n\n" not in content
```
Aggiungere a `tests/test_templates.py`:
```python
def test_entry_to_markdown_skips_empty_intro():
    from mcp_cronos.templates import Entry

    md = Entry(progetto="P", descrizione="D", paragrafo_intro="").to_markdown()
    # Header present, no empty intro paragraph producing a blank-only line run.
    assert md.startswith("### P - D")
    assert "\n\n\n" not in md
```
Run mirato → FAIL (paragrafo_intro obbligatorio nella firma del tool / chiamata; e render aggiunge riga vuota).

NOTE: `aggiungi_entry(progetto=..., descrizione=..., data=...)` senza `paragrafo_intro` fallira' finche' il parametro e' obbligatorio: lo si rende opzionale nello Step 2.

- [ ] **Step 2: rendere paragrafo_intro opzionale (entries.py)**

Nella firma di `aggiungi_entry`, cambiare `paragrafo_intro: str` in `paragrafo_intro: str = ""`. Spostarlo dopo i parametri obbligatori NON e' necessario perche' ha gia' un default tra parametri con default; ma Python richiede che i parametri senza default precedano quelli con default. `paragrafo_intro` e' il terzo parametro, seguito da `contenuto: str = ""` (gia' con default). Mettere `paragrafo_intro: str = ""` mantiene l'ordine valido (i successivi hanno gia' default). Verificare che la firma resti sintatticamente valida.

- [ ] **Step 3: render salta intro vuoto (templates.py)**

In `Entry.to_markdown`, sostituire:
```python
        # Paragrafo introduttivo
        lines.append(self.paragrafo_intro)
        lines.append("")
```
con:
```python
        # Introductory paragraph (skip when empty to avoid a blank line run).
        if self.paragrafo_intro:
            lines.append(self.paragrafo_intro)
            lines.append("")
```

- [ ] **Step 4: server.py — rimuovere paragrafo_intro dai required**

Nella `Tool(name="cronos_aggiungi_entry", ...)`, cambiare `"required": ["progetto", "descrizione", "paragrafo_intro"]` in `"required": ["progetto", "descrizione"]`. Lasciare `paragrafo_intro` fra le `properties`, aggiornandone la descrizione per indicarlo opzionale.

- [ ] **Step 5: verificare**

Run: `uv run pytest tests/test_entries.py tests/test_templates.py -v` → verdi.
Run: `uv run pytest -q` → verde (attenzione: test esistenti che creano entry CON intro devono restare invariati). `ruff check` pulito.

- [ ] **Step 6: commit**

```bash
git add src/mcp_cronos/tools/entries.py src/mcp_cronos/templates.py src/mcp_cronos/server.py tests/test_entries.py tests/test_templates.py
git commit -m "feat(entries): make paragrafo_intro optional

CHANGE: paragrafo_intro defaults to empty and is dropped from the required tool
inputs; Entry.to_markdown skips an empty intro so no blank paragraph is rendered.
progetto and descrizione remain required (project is never guessed)."
```

---

## Task 4: C4 — chiusura serale unica

**Files:** Modify `src/mcp_cronos/tools/scrivi_fine_giornata.py`, `src/mcp_cronos/server.py`; Test `tests/test_scrivi.py`.

- [ ] **Step 1: test che fallisce**

Aggiungere a `tests/test_scrivi.py` (usare config con git disabilitato per evitare commit reali; il fixture `config_toml_it`/`config_toml_en` imposta `git = false`):
```python
def test_scrivi_fine_giornata_with_contenuto_todo_prepares_next_day(tmp_diario, config_toml_it):
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.scrivi_fine_giornata import scrivi_fine_giornata

    _reset_config()
    result = scrivi_fine_giornata(
        contenuto="# Chiusura\n\nfatto.\n",
        data="2026-04-09",
        contenuto_todo="- [ ] domani task\n",
    )
    assert result["successo"] is True
    assert "prepara_domani" in result
    assert result["prepara_domani"]["successo"] is True
    from pathlib import Path
    assert Path(result["prepara_domani"]["todo_file"]).exists()


def test_scrivi_fine_giornata_without_todo_unchanged(tmp_diario, config_toml_it):
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.scrivi_fine_giornata import scrivi_fine_giornata

    _reset_config()
    result = scrivi_fine_giornata(contenuto="# Chiusura\n\nfatto.\n", data="2026-04-09")
    assert result["successo"] is True
    assert "prepara_domani" not in result
```
Run mirato → FAIL (param `contenuto_todo` assente).

- [ ] **Step 2: estendere scrivi_fine_giornata**

In `src/mcp_cronos/tools/scrivi_fine_giornata.py`, aggiungere l'import:
```python
from mcp_cronos.tools.prepara_domani import prepara_domani
```
Aggiungere `contenuto_todo: Optional[str] = None` alla firma di `scrivi_fine_giornata` (dopo `data`) e documentarlo. Prima del `return` finale, dopo aver calcolato `git_result`, costruire il dict di ritorno in una variabile e, se `contenuto_todo` e' fornito, agganciare la preparazione del domani:
```python
    risultato = {
        "successo": True,
        "file": str(file_path),
        "data": str(file_date),
        "dimensione": len(contenuto),
        "messaggio": f"File di fine giornata scritto per {file_date}",
        "git": git_result,
    }
    if contenuto_todo is not None:
        risultato["prepara_domani"] = prepara_domani(contenuto_todo)
    return risultato
```
(Sostituisce il `return { ... }` attuale.)

- [ ] **Step 3: server.py — schema + dispatch**

Nella `Tool(name="cronos_scrivi_fine_giornata", ...)`, aggiungere a `properties`:
```python
                "contenuto_todo": {
                    "type": "string",
                    "description": (
                        "Se fornito, dopo la scrittura prepara la cartella del prossimo "
                        "giorno lavorativo con questo todo.md (opzionale)"
                    ),
                },
```
e una riga nella descrizione testuale del tool. Nel dispatch `elif name == "cronos_scrivi_fine_giornata":`, aggiungere:
```python
                contenuto_todo=arguments.get("contenuto_todo"),
```

- [ ] **Step 4: verificare**

Run: `uv run pytest tests/test_scrivi.py -v` → verdi.
Run: `uv run pytest -q` → verde. `ruff check` pulito.

- [ ] **Step 5: commit**

```bash
git add src/mcp_cronos/tools/scrivi_fine_giornata.py src/mcp_cronos/server.py tests/test_scrivi.py
git commit -m "feat(fine-giornata): optionally prepare next day on write

CHANGE: scrivi_fine_giornata accepts an optional contenuto_todo; when provided it
prepares the next working day's folder via prepara_domani after writing and
committing the closure, returning the result under 'prepara_domani'. Without it,
behaviour is unchanged."
```

---

## Task 5: Documentazione

**Files:** Modify `README.md`, `CLAUDE.md`.

- [ ] **Step 1: README (entrambe le lingue)**

- In `cronos_aggiungi_entry` e `cronos_aggiungi_a_progetto`: aggiungere il parametro opzionale `working_dir` (directory git da cui rilevare repository/branch se omessi) e indicare che `repository`/`branch` vengono rilevati da git quando non forniti; segnalare `paragrafo_intro` come opzionale in `cronos_aggiungi_entry`.
- In `cronos_scrivi_fine_giornata`: aggiungere il parametro opzionale `contenuto_todo` e spiegare che prepara il prossimo giorno lavorativo.

- [ ] **Step 2: CLAUDE.md**

Aggiungere `gitinfo` alla lista degli scope di commit e citare brevemente, nel "Tool workflow", che gli strumenti di entry rilevano repo/branch da git e che la chiusura serale puo' preparare il domani in un colpo.

- [ ] **Step 3: commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: document git auto-detect, optional intro, one-step evening close

CHANGE: Documents the working_dir parameter and git auto-detection of
repository/branch, the now-optional paragrafo_intro, and the contenuto_todo
option on scrivi_fine_giornata, in README (both languages) and CLAUDE.md."
```

---

## Chiusura C2-C4

- [ ] **Step finale:** `uv run pytest -q` verde; `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` puliti. Branch pronto per il merge (decisione utente, mai push automatico).

## Note di esecuzione
- Test-first per ogni task.
- Ordine: C2 modulo (T1) prima dell'integrazione (T2); C3 (T3); C4 (T4); doc (T5).
- I test git usano `git init -b <branch>` + un commit per avere un branch determinato; se l'ambiente non avesse git, i test di rilevamento fallirebbero: in tal caso fermarsi e segnalare (non e' un caso da aggirare, git c'e' in questo ambiente).
- Non dedurre il progetto: progetto e descrizione restano obbligatori.
