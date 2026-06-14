# Piano di implementazione — Calendario consapevole dei festivi (C1)

> **Per worker agentici:** SUB-SKILL RICHIESTA: superpowers:subagent-driven-development. Step a checkbox (`- [ ]`).

**Obiettivo:** far saltare i giorni festivi (oltre ai weekend) al calcolo del prossimo e dell'ultimo giorno lavorativo, usando la libreria `holidays` (default Italia, paese configurabile) piu' date extra definite dall'utente in `cronos.toml`.

**Architettura:** nuovo modulo `utils/workdays.py` espone `is_holiday`/`is_working_day` leggendo paese e date extra da `CronosConfig`. `dates.py` riscrive `get_next_working_day` e aggiunge `get_previous_working_day` come cicli basati su `is_working_day`. `standup.py` usa `get_previous_working_day`. Nessun import circolare: `workdays` dipende da `config`, non da `dates`.

**Stack:** Python 3.10+, libreria `holidays`, pytest, ruff.

**Riferimento spec:** `docs/specs/2026-06-14-holiday-aware-calendar-design.md`

**Lingua:** codice/commit in inglese; piano/spec in italiano.

---

## Struttura dei file toccati

- `pyproject.toml` + `uv.lock` (modifica): dipendenza `holidays`.
- `src/mcp_cronos/config.py` (modifica): `calendar_country`, `calendar_extra_holidays`.
- `src/mcp_cronos/utils/workdays.py` (nuovo): `is_holiday`, `is_working_day`.
- `src/mcp_cronos/utils/dates.py` (modifica): `get_next_working_day` (riscritto), `get_previous_working_day` (nuovo).
- `src/mcp_cronos/tools/standup.py` (modifica): `_ultimo_giorno_lavorativo` usa `get_previous_working_day`.
- `tests/test_config.py`, `tests/test_workdays.py` (nuovo), `tests/test_dates.py`, `tests/test_standup.py` (modifica/aggiunta).
- `README.md`, `CLAUDE.md` (modifica): sezione `[cronos.calendar]`.

---

## Task 1: Config — paese e festivi extra

**Files:**
- Modify: `src/mcp_cronos/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: test che fallisce**

Aggiungere a `tests/test_config.py`:

```python
def test_config_calendar_defaults(tmp_diario):
    from mcp_cronos.config import load_config

    config = load_config()
    assert config.calendar_country == "IT"
    assert config.calendar_extra_holidays == []


def test_config_calendar_overrides(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n'
        '[cronos.calendar]\ncountry = "FR"\n'
        'extra_holidays = ["2026-12-07", "2026-08-14"]\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config, load_config

    _reset_config()
    config = load_config()
    assert config.calendar_country == "FR"
    assert config.calendar_extra_holidays == ["2026-12-07", "2026-08-14"]
```

- [ ] **Step 2: verificare il fallimento**

Run: `uv run pytest tests/test_config.py -k calendar -v` → FAIL (campi assenti).

- [ ] **Step 3: aggiungere i campi al dataclass**

In `src/mcp_cronos/config.py`, in `CronosConfig`, dopo `section_requested_by: str` aggiungere:

```python
    calendar_country: str
    calendar_extra_holidays: list[str]
```

- [ ] **Step 4: risolverli in load_config**

In `load_config()`, dopo il blocco delle etichette (dopo `section_requested_by = ...`) e prima della costruzione `_config = CronosConfig(...)`, aggiungere:

```python
    # Calendar settings: national-holiday country code + user extra holidays.
    user_calendar: dict[str, Any] = cronos_section.get("calendar", {})
    calendar_country: str = user_calendar.get("country", "IT")
    raw_extra = user_calendar.get("extra_holidays", [])
    calendar_extra_holidays: list[str] = (
        [str(x) for x in raw_extra] if isinstance(raw_extra, list) else []
    )
```

Nel costruttore `_config = CronosConfig(...)` aggiungere (dopo `section_requested_by=section_requested_by,`):

```python
        calendar_country=calendar_country,
        calendar_extra_holidays=calendar_extra_holidays,
```

- [ ] **Step 5: verificare**

Run: `uv run pytest tests/test_config.py -k calendar -v` → PASS.
Run: `uv run pytest -q` → suite verde.
Run: `uv run ruff check src/mcp_cronos/config.py tests/test_config.py` → pulito.

- [ ] **Step 6: commit**

```bash
git add src/mcp_cronos/config.py tests/test_config.py
git commit -m "feat(config): add calendar country and extra holidays settings

CHANGE: CronosConfig now exposes calendar_country (default IT) and
calendar_extra_holidays, resolved from the optional [cronos.calendar] section of
cronos.toml. Foundation for holiday-aware working-day calculation."
```

---

## Task 2: Dipendenza + modulo workdays

**Files:**
- Modify: `pyproject.toml` (via `uv add`)
- Create: `src/mcp_cronos/utils/workdays.py`
- Test: `tests/test_workdays.py` (nuovo)

- [ ] **Step 1: aggiungere la dipendenza**

Run: `uv add holidays`
Verificare che `pyproject.toml` `dependencies` ora includa una riga `holidays>=...` e che `uv.lock` sia aggiornato. Confermare l'import: `uv run python -c "import holidays; print(holidays.__name__)"`.

- [ ] **Step 2: test che fallisce**

Creare `tests/test_workdays.py`:

```python
"""Tests for mcp_cronos.utils.workdays (holiday and working-day helpers)."""

from datetime import date


def test_is_holiday_fixed_national(tmp_diario):
    from mcp_cronos.utils.workdays import is_holiday

    assert is_holiday(date(2026, 12, 25)) is True  # Natale


def test_is_holiday_easter_monday(tmp_diario):
    from mcp_cronos.utils.workdays import is_holiday

    assert is_holiday(date(2026, 4, 6)) is True  # Pasquetta 2026 (mobile)


def test_is_holiday_false_on_plain_weekday(tmp_diario):
    from mcp_cronos.utils.workdays import is_holiday

    assert is_holiday(date(2026, 5, 5)) is False  # martedi feriale


def test_is_holiday_extra_from_config(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n'
        '[cronos.calendar]\nextra_holidays = ["2026-07-20"]\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.workdays import is_holiday

    _reset_config()
    assert is_holiday(date(2026, 7, 20)) is True  # ponte configurato


def test_is_working_day(tmp_diario):
    from mcp_cronos.utils.workdays import is_working_day

    assert is_working_day(date(2026, 5, 5)) is True   # martedi feriale
    assert is_working_day(date(2026, 5, 9)) is False  # sabato
    assert is_working_day(date(2026, 12, 25)) is False  # Natale (venerdi festivo)


def test_invalid_country_falls_back_without_raising(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n[cronos.calendar]\ncountry = "ZZ"\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.workdays import is_holiday

    _reset_config()
    # No exception; unknown country yields no national holidays.
    assert is_holiday(date(2026, 12, 25)) is False
```

- [ ] **Step 3: verificare il fallimento**

Run: `uv run pytest tests/test_workdays.py -v` → FAIL (modulo assente).

- [ ] **Step 4: creare il modulo**

Creare `src/mcp_cronos/utils/workdays.py`:

```python
"""Working-day and holiday helpers.

Determines whether a date is a public holiday (national calendar for the
configured country, plus user-defined extra holidays) and whether it is a
working day (a weekday that is not a holiday). Used by the next/previous
working-day calculations so day planning skips both weekends and holidays.
"""

from datetime import date

import holidays

from mcp_cronos.config import load_config


def is_holiday(d: date) -> bool:
    """Return True if d is a holiday for the configured country or an extra holiday.

    The national calendar comes from the `holidays` library, which expands years
    on demand. Extra holidays are user-configured YYYY-MM-DD strings. An unknown
    or unsupported country code falls back to extra holidays only and never
    raises, so a misconfiguration cannot break working-day calculation.
    """
    config = load_config()
    if d.isoformat() in set(config.calendar_extra_holidays):
        return True
    try:
        national = holidays.country_holidays(config.calendar_country)
    except (KeyError, NotImplementedError):
        return False
    return d in national


def is_working_day(d: date) -> bool:
    """Return True if d is a weekday (Mon-Fri) and not a holiday."""
    return d.weekday() < 5 and not is_holiday(d)
```

- [ ] **Step 5: verificare**

Run: `uv run pytest tests/test_workdays.py -v` → PASS.
Run: `uv run pytest -q` → suite verde.
Run: `uv run ruff check src/mcp_cronos/utils/workdays.py tests/test_workdays.py` → pulito.

- [ ] **Step 6: commit**

```bash
git add pyproject.toml uv.lock src/mcp_cronos/utils/workdays.py tests/test_workdays.py
git commit -m "feat(workdays): add holiday and working-day helpers

CHANGE: New utils/workdays.py with is_holiday and is_working_day, backed by the
holidays library for the configured country plus user extra_holidays. Unknown
country codes fall back to extra holidays only without raising. Adds the
holidays dependency."
```

---

## Task 3: Calcolo giorni lavorativi festivo-aware

**Files:**
- Modify: `src/mcp_cronos/utils/dates.py`
- Modify: `src/mcp_cronos/tools/standup.py`
- Test: `tests/test_dates.py`, `tests/test_standup.py`

- [ ] **Step 1: test che falliscono**

Aggiungere a `tests/test_dates.py` (nella sezione `get_next_working_day`):

```python
def test_get_next_working_day_skips_christmas_cluster(tmp_diario):
    """Thu 2026-12-24 -> Mon 2026-12-28 (skips Christmas, Santo Stefano, weekend)."""
    from mcp_cronos.utils.dates import get_next_working_day

    assert get_next_working_day(date(2026, 12, 24)) == date(2026, 12, 28)


def test_get_next_working_day_skips_easter_monday(tmp_diario):
    """Fri 2026-04-03 -> Tue 2026-04-07 (skips weekend and Easter Monday 04-06)."""
    from mcp_cronos.utils.dates import get_next_working_day

    assert get_next_working_day(date(2026, 4, 3)) == date(2026, 4, 7)


def test_get_next_working_day_skips_extra_holiday(tmp_diario):
    """With 2026-12-07 as an extra holiday: Fri 2026-12-04 -> Wed 2026-12-09
    (skips weekend, the configured 12-07, and Immacolata 12-08)."""
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n'
        '[cronos.calendar]\nextra_holidays = ["2026-12-07"]\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.dates import get_next_working_day

    _reset_config()
    assert get_next_working_day(date(2026, 12, 4)) == date(2026, 12, 9)


def test_get_previous_working_day_skips_christmas_cluster(tmp_diario):
    """Mon 2026-12-28 -> Thu 2026-12-24 (skips weekend, Santo Stefano, Christmas)."""
    from mcp_cronos.utils.dates import get_previous_working_day

    assert get_previous_working_day(date(2026, 12, 28)) == date(2026, 12, 24)
```

- [ ] **Step 2: verificare il fallimento**

Run: `uv run pytest tests/test_dates.py -k "christmas or easter or extra_holiday or previous_working" -v` → FAIL.

- [ ] **Step 3: riscrivere get_next_working_day e aggiungere get_previous_working_day**

In `src/mcp_cronos/utils/dates.py`, aggiungere l'import in cima (con gli altri import del package):

```python
from mcp_cronos.utils.workdays import is_working_day
```

Sostituire l'intera funzione `get_next_working_day` con:

```python
def get_next_working_day(from_date: date) -> date:
    """
    Return the next working day strictly after from_date.

    Skips weekends and holidays by advancing one day at a time until a working
    day is found. Naturally handles holiday clusters (e.g. 25-26 December) and
    user-configured extra holidays. The 366-iteration cap is a safety bound
    against a pathological config that marks every day as a holiday.

    Args:
        from_date: Starting date.

    Returns:
        Date of the next working day.
    """
    candidate = from_date + timedelta(days=1)
    for _ in range(366):
        if is_working_day(candidate):
            return candidate
        candidate += timedelta(days=1)
    return candidate


def get_previous_working_day(from_date: date) -> date:
    """
    Return the most recent working day strictly before from_date.

    Mirror of get_next_working_day: steps backward one day at a time, skipping
    weekends and holidays, with the same 366-iteration safety bound.

    Args:
        from_date: Starting date.

    Returns:
        Date of the previous working day.
    """
    candidate = from_date - timedelta(days=1)
    for _ in range(366):
        if is_working_day(candidate):
            return candidate
        candidate -= timedelta(days=1)
    return candidate
```

(Verificare che il vecchio corpo a delta fissi sia rimosso del tutto e che `timedelta` resti importato.)

- [ ] **Step 4: refactor standup**

In `src/mcp_cronos/tools/standup.py`, aggiungere `get_previous_working_day` all'import esistente da `mcp_cronos.utils.dates`. Sostituire il corpo di `_ultimo_giorno_lavorativo`:

```python
def _ultimo_giorno_lavorativo(oggi: date) -> date:
    """
    Calcola l'ultimo giorno lavorativo (lun-ven, esclusi i festivi) prima di oggi.

    Delega a get_previous_working_day cosi' da saltare anche i festivi, non solo
    il weekend.

    Args:
        oggi: Data odierna

    Returns:
        Data dell'ultimo giorno lavorativo
    """
    return get_previous_working_day(oggi)
```

(Se dopo questa modifica `timedelta` non e' piu' usato in `standup.py`, rimuovere l'import inutilizzato per non far fallire ruff; verificare con `ruff check`.)

- [ ] **Step 5: verificare**

Run: `uv run pytest tests/test_dates.py -v` → tutti verdi (nuovi + i preesistenti di maggio).
Run: `uv run pytest tests/test_standup.py -v` → verdi.
Run: `uv run pytest -q` → suite verde.
Run: `uv run ruff check src/mcp_cronos/utils/dates.py src/mcp_cronos/tools/standup.py tests/test_dates.py` → pulito.

- [ ] **Step 6: commit**

```bash
git add src/mcp_cronos/utils/dates.py src/mcp_cronos/tools/standup.py tests/test_dates.py
git commit -m "feat(dates): make working-day calculation holiday-aware

CHANGE: get_next_working_day now loops over is_working_day so it skips holidays
and holiday clusters, not just weekends; adds get_previous_working_day as the
backward mirror. standup's last-working-day helper delegates to it. Fixes
prepara_domani landing on a holiday."
```

---

## Task 4: Documentazione

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: README — sezione `[cronos.calendar]` (entrambe le lingue)**

Nel blocco `cronos.toml` del README (sezione English e sezione Italiano), dopo il sotto-blocco `[cronos.git]`, aggiungere la documentazione della nuova sezione, con commenti coerenti allo stile esistente:

```toml
[cronos.calendar]
# ISO country code for the national holiday calendar (default "IT").
country = "IT"
# Extra dates treated as holidays (bridges, company closures), YYYY-MM-DD.
extra_holidays = ["2026-12-07"]
```

Aggiungere una frase (in entrambe le lingue) che spiega: il calcolo del prossimo
e dell'ultimo giorno lavorativo (usato da `cronos_prepara_domani` e dallo
standup) salta i festivi nazionali del paese configurato piu' le `extra_holidays`,
oltre ai weekend.

- [ ] **Step 2: CLAUDE.md — configurazione e dipendenza**

Nel `CLAUDE.md`, sezione "Configuration system", aggiungere una riga che cita la
sezione `[cronos.calendar]` (country + extra_holidays) e il comportamento
festivo-aware. Nello "Stack" in cima all'Architecture, aggiungere `holidays` fra
le librerie. Aggiungere `workdays` alla lista degli scope di commit.

- [ ] **Step 3: commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: document holiday-aware calendar configuration

CHANGE: Documents the [cronos.calendar] section (country, extra_holidays) and
the holiday-aware next/previous working-day behaviour in README (both languages)
and CLAUDE.md, and notes the holidays dependency."
```

---

## Chiusura C1

- [ ] **Step finale: suite + lint**

Run: `uv run pytest -q` → tutti verdi.
Run: `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` → puliti.

Branch `feature/holiday-aware-calendar` pronto per il merge (decisione utente, mai push automatico).

---

## Note di esecuzione

- Test-first in ogni task.
- Ordine obbligatorio: config (Task 1) prima di workdays (Task 2, lo usa), prima di dates/standup (Task 3, usa workdays).
- I test di `get_next_working_day` di maggio 2026 NON cadono su festivi italiani: devono restare verdi senza modifiche; se per qualsiasi motivo uno fallisse, fermarsi ed escalare invece di indebolirlo.
- Se la libreria `holidays` espone un'API diversa da `holidays.country_holidays(country)` nella versione installata, fermarsi e segnalarlo invece di improvvisare.
