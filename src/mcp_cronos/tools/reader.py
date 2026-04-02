"""
Tool per la lettura del diario.

Funzioni:
- leggi_diario: Legge entry per data o range di date
- lista_progetti: Elenca i progetti menzionati in un periodo
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from mcp_cronos.config import get_diario_path
from mcp_cronos.utils.dates import (
    get_file_path,
    get_today,
    parse_date,
    get_date_range,
)
from mcp_cronos.utils.markdown import parse_diary_file, extract_projects


def leggi_diario(
    data: Optional[str] = None,
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: Optional[int] = None,
) -> dict:
    """
    Legge il contenuto del diario per una data o range di date.

    Modalita' di utilizzo (mutualmente esclusive):
    1. data: Legge un singolo giorno
    2. data_inizio + data_fine: Legge un range di date
    3. ultimi_giorni: Legge gli ultimi N giorni (default 7)
    4. Nessun parametro: Legge il diario di oggi

    Args:
        data: Data singola in formato YYYY-MM-DD
        data_inizio: Data inizio range in formato YYYY-MM-DD
        data_fine: Data fine range in formato YYYY-MM-DD
        ultimi_giorni: Numero di giorni da leggere (partendo da oggi)

    Returns:
        Dict con contenuto del diario e metadati
    """
    today = get_today()

    # Determina le date da leggere
    if data:
        try:
            dates_to_read = [parse_date(data)]
        except ValueError as e:
            return {"errore": str(e)}
    elif data_inizio and data_fine:
        try:
            start = parse_date(data_inizio)
            end = parse_date(data_fine)
            if start > end:
                return {"errore": "data_inizio deve essere precedente a data_fine"}
            dates_to_read = get_date_range(start, end)
        except ValueError as e:
            return {"errore": str(e)}
    elif ultimi_giorni:
        start = today - timedelta(days=ultimi_giorni - 1)
        dates_to_read = get_date_range(start, today)
    else:
        # Default: oggi
        dates_to_read = [today]

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
                    entries_data.append({
                        "progetto": entry.progetto,
                        "descrizione": entry.descrizione,
                        "richiesto_da": entry.richiesto_da,
                        "contenuto_preview": entry.contenuto[:200] + "..." if len(entry.contenuto) > 200 else entry.contenuto,
                        "riferimenti": entry.riferimenti
                    })

                risultati.append({
                    "data": str(d),
                    "file": str(file_path),
                    "titolo": diary.titolo,
                    "entries": entries_data,
                    "num_entries": len(diary.entries),
                    "bloccanti": diary.bloccanti
                })
        else:
            files_mancanti += 1
            risultati.append({
                "data": str(d),
                "file": str(file_path),
                "esiste": False,
                "messaggio": "File non trovato"
            })

    # Riepilogo
    return {
        "periodo": {
            "da": str(dates_to_read[0]),
            "a": str(dates_to_read[-1]),
            "giorni_totali": len(dates_to_read)
        },
        "riepilogo": {
            "files_trovati": files_trovati,
            "files_mancanti": files_mancanti
        },
        "giorni": risultati
    }


def lista_progetti(
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 30,
) -> dict:
    """
    Elenca i progetti menzionati nel diario in un periodo.

    Utile per avere una panoramica dei progetti su cui si e' lavorato.

    Args:
        data_inizio: Data inizio in formato YYYY-MM-DD (opzionale)
        data_fine: Data fine in formato YYYY-MM-DD (opzionale)
        ultimi_giorni: Se non specificate le date, usa gli ultimi N giorni (default 30)

    Returns:
        Dict con lista progetti e statistiche
    """
    today = get_today()

    # Determina le date
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

    dates_to_read = get_date_range(start, end)

    # Raccogli progetti e conteggi
    progetti_count: dict[str, int] = {}
    progetti_date: dict[str, list[str]] = {}

    for d in dates_to_read:
        file_path = get_file_path(d)

        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            projects = extract_projects(content)

            for proj in projects:
                progetti_count[proj] = progetti_count.get(proj, 0) + 1
                if proj not in progetti_date:
                    progetti_date[proj] = []
                progetti_date[proj].append(str(d))

    # Ordina per frequenza
    progetti_ordinati = sorted(
        progetti_count.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # Formatta risultato
    progetti_dettaglio = []
    for proj, count in progetti_ordinati:
        progetti_dettaglio.append({
            "nome": proj,
            "occorrenze": count,
            "date": progetti_date[proj]
        })

    return {
        "periodo": {
            "da": str(start),
            "a": str(end),
            "giorni_analizzati": len(dates_to_read)
        },
        "totale_progetti": len(progetti_count),
        "progetti": progetti_dettaglio
    }