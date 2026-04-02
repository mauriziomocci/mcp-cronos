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
            testo_completo = f"{entry.progetto} {entry.descrizione} {entry.contenuto}"
            matches = pattern.findall(testo_completo)

            if matches:
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