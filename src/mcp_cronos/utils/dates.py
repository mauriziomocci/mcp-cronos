"""
Utility per la gestione delle date nel diario.

Le date nel diario seguono queste convenzioni:
- File: {anno}/{mese}/{anno}-{mese}-{giorno}.md (es. 2026/01/2026-01-21.md)
- Titolo: "Per lo Stand-up {Giorno+1} {Mese} {Anno}" (es. "Per lo Stand-up 22 Gennaio 2026")
- I mesi sono in italiano
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from mcp_cronos.config import get_diario_path


# Mesi in italiano
MESI_ITALIANI = [
    "Gennaio", "Febbraio", "Marzo", "Aprile",
    "Maggio", "Giugno", "Luglio", "Agosto",
    "Settembre", "Ottobre", "Novembre", "Dicembre"
]


def get_today() -> date:
    """Restituisce la data odierna."""
    return date.today()


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
    Formatta la data dello stand-up in italiano.

    Args:
        standup_date: Data dello stand-up

    Returns:
        Stringa formattata (es. "22 Gennaio 2026")
    """
    giorno = standup_date.day
    mese = MESI_ITALIANI[standup_date.month - 1]
    anno = standup_date.year
    return f"{giorno} {mese} {anno}"


def get_standup_title(file_date: date) -> str:
    """
    Genera il titolo per lo stand-up.

    Args:
        file_date: Data del file del diario

    Returns:
        Titolo formattato (es. "Per lo Stand-up 22 Gennaio 2026")
    """
    standup_date = get_standup_date(file_date)
    return f"Per lo Stand-up {format_standup_date(standup_date)}"


def get_file_path(file_date: date, diario_path: Optional[Path] = None) -> Path:
    """
    Calcola il path del file per una data specifica.

    Args:
        file_date: Data per cui calcolare il path
        diario_path: Path base del diario (opzionale, usa config se non specificato)

    Returns:
        Path completo del file (es. /path/to/Diario/2026/01/2026-01-21.md)
    """
    if diario_path is None:
        diario_path = get_diario_path()

    anno = file_date.strftime("%Y")
    mese = file_date.strftime("%m")
    filename = file_date.strftime("%Y-%m-%d.md")

    return diario_path / anno / mese / filename


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