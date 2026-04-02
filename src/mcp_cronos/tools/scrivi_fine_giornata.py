"""
Tool per scrivere il file di fine giornata.

Riceve il contenuto markdown generato dall'LLM dopo cronos_fine_giornata
e lo scrive al file del diario corretto.
"""

from typing import Optional

from mcp_cronos.utils.dates import get_file_path, get_today, parse_date, ensure_directory_exists


def scrivi_fine_giornata(
    contenuto: str,
    data: Optional[str] = None,
) -> dict:
    """
    Scrive il file di fine giornata con il contenuto generato dall'LLM.

    Args:
        contenuto: Contenuto markdown completo del file (con tutte le sezioni)
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

    file_path.write_text(contenuto, encoding="utf-8")

    return {
        "successo": True,
        "file": str(file_path),
        "data": str(file_date),
        "dimensione": len(contenuto),
        "messaggio": f"File di fine giornata scritto per {file_date}"
    }
