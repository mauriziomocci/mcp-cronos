"""
Utility per la gestione delle date nel diario.

Convenzioni di layout:
- Legacy (storico): {anno}/{mese}/{anno}-{mese}-{giorno}.md
  Esempio: 2026/04/2026-04-30.md
  File singolo che contiene sia le entry raw sia la chiusura giornata.

- Nuovo layout (giorni futuri): {anno}/{mese}/{anno}-{mese}-{giorno}/
  Esempio: 2026/05/2026-05-04/raw.md + fine-giornata.md
  Cartella per giorno con due file separati:
    - raw.md: progressive log delle entry, bloccanti, consolidamenti
    - fine-giornata.md: chiusura snella e fruibile

Regola di transizione:
- Se per una data esiste il file legacy, viene usato il legacy (no migrazione).
- Altrimenti viene usato il nuovo layout, anche per giorni che non esistono
  ancora (e.g. prima entry di oggi).

Titolo: format_title() from the active language pack
       (es. "Per lo Stand-up - 22 Gennaio 2026")
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from mcp_cronos.config import get_diario_path, load_config
from mcp_cronos.i18n import get_language_pack
from mcp_cronos.utils.workdays import is_working_day


def get_today() -> date:
    """Restituisce la data odierna."""
    return date.today()


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


def parse_date(date_str: str) -> date:
    """
    Converte una stringa data in oggetto date.

    Args:
        date_str: Data in formato YYYY-MM-DD

    Returns:
        Oggetto date

    Raises:
        ValueError: Se il formato non e' valido
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Formato data non valido: '{date_str}'. Usare YYYY-MM-DD")


def get_standup_date(file_date: date) -> date:
    """
    Calcola la data dello stand-up (giorno+1).

    Args:
        file_date: Data del file del diario

    Returns:
        Data dello stand-up (giorno successivo)
    """
    return file_date + timedelta(days=1)


def format_standup_date(standup_date: date) -> str:
    """
    Format the standup date using the language pack from the active config.

    Delegates to LanguagePack.format_date so that the output respects the
    configured locale (e.g. "22 Gennaio 2026" for Italian, "January 22, 2026"
    for English) without any hardcoded month names in this module.

    Args:
        standup_date: Date of the standup

    Returns:
        Locale-formatted date string.
    """
    config = load_config()
    pack = get_language_pack(config.lang)
    return pack.format_date(standup_date)


def get_standup_title(file_date: date) -> str:
    """
    Generate the standup title for the given diary file date.

    Uses the language pack from the active config so that both the prefix and
    date format honour the configured locale.

    Args:
        file_date: Date of the diary file

    Returns:
        Full standup title (e.g. "Per lo Stand-up - 22 Gennaio 2026").
    """
    config = load_config()
    pack = get_language_pack(config.lang)
    standup_date = get_standup_date(file_date)
    return pack.format_title(standup_date)


def _diario_root(diario_path: Optional[Path]) -> Path:
    """Risolve il root del diario, accettando override esplicito."""
    return diario_path if diario_path is not None else get_diario_path()


def get_legacy_file_path(file_date: date, diario_path: Optional[Path] = None) -> Path:
    """
    Path del file legacy single-file per una data.

    Esempio: /path/to/Diario/2026/04/2026-04-30.md
    """
    root = _diario_root(diario_path)
    anno = file_date.strftime("%Y")
    mese = file_date.strftime("%m")
    filename = file_date.strftime("%Y-%m-%d.md")
    return root / anno / mese / filename


def get_day_folder_path(file_date: date, diario_path: Optional[Path] = None) -> Path:
    """
    Path della cartella giornaliera nel nuovo layout.

    Esempio: /path/to/Diario/2026/05/2026-05-04/
    """
    root = _diario_root(diario_path)
    anno = file_date.strftime("%Y")
    mese = file_date.strftime("%m")
    folder = file_date.strftime("%Y-%m-%d")
    return root / anno / mese / folder


def get_raw_path(file_date: date, diario_path: Optional[Path] = None) -> Path:
    """
    Path del file `raw.md` nel nuovo layout (progressive log della giornata).

    Esempio: /path/to/Diario/2026/05/2026-05-04/raw.md
    """
    return get_day_folder_path(file_date, diario_path) / "raw.md"


def get_fine_giornata_path(file_date: date, diario_path: Optional[Path] = None) -> Path:
    """
    Path del file `fine-giornata.md` nel nuovo layout (chiusura giornata).

    Esempio: /path/to/Diario/2026/05/2026-05-04/fine-giornata.md
    """
    return get_day_folder_path(file_date, diario_path) / "fine-giornata.md"


def get_todo_path(file_date: date, diario_path: Optional[Path] = None) -> Path:
    """
    Path del file `todo.md` nel nuovo layout (lista cose da fare per la giornata).

    Esiste solo nel nuovo layout cartella per giorno: i diari legacy non
    hanno mai avuto un todo separato, quindi non c'e' fallback retroattivo.

    Esempio: /path/to/Diario/2026/05/2026-05-04/todo.md
    """
    return get_day_folder_path(file_date, diario_path) / "todo.md"


def has_legacy_file(file_date: date, diario_path: Optional[Path] = None) -> bool:
    """True se per la data esiste il file legacy single-file."""
    return get_legacy_file_path(file_date, diario_path).exists()


def resolve_raw_path(file_date: date, diario_path: Optional[Path] = None) -> Path:
    """
    Path su cui scrivere/leggere le entry raw della giornata.

    - Se esiste il legacy single-file, restituisce quello (no migrazione).
    - Altrimenti restituisce il path `raw.md` nel nuovo layout (anche se
      la cartella non esiste ancora; il chiamante creera' i parent).
    """
    if has_legacy_file(file_date, diario_path):
        return get_legacy_file_path(file_date, diario_path)
    return get_raw_path(file_date, diario_path)


def resolve_fine_giornata_path(file_date: date, diario_path: Optional[Path] = None) -> Path:
    """
    Path su cui scrivere/leggere la chiusura giornata.

    - Se esiste il legacy single-file, restituisce quello: la chiusura
      sostituisce o si appende al file unico, come faceva prima del refactor.
    - Altrimenti restituisce il path `fine-giornata.md` nel nuovo layout.
    """
    if has_legacy_file(file_date, diario_path):
        return get_legacy_file_path(file_date, diario_path)
    return get_fine_giornata_path(file_date, diario_path)


def get_file_path(file_date: date, diario_path: Optional[Path] = None) -> Path:
    """
    Backward-compat: path del file principale per una data.

    Mantenuto per i tool che ancora ragionano in termini di "file unico"
    (lettura, ricerca, settimana). Risolve come `resolve_raw_path`: legacy
    se esiste, altrimenti `raw.md` nel nuovo layout.
    """
    return resolve_raw_path(file_date, diario_path)


def ensure_directory_exists(file_path: Path) -> None:
    """
    Crea la directory per il file se non esiste.

    Args:
        file_path: Path del file
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)


def get_date_range(start_date: date, end_date: date) -> list[date]:
    """
    Genera una lista di date tra start_date e end_date (inclusi).

    Args:
        start_date: Data di inizio
        end_date: Data di fine

    Returns:
        Lista di date
    """
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates
