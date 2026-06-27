"""
Tool per la lettura del diario.

Funzioni:
- leggi_diario: Legge entry per data o range di date
- lista_progetti: Elenca i progetti menzionati in un periodo
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.utils.dates import (
    get_date_range,
    get_file_path,
    get_today,
    parse_date,
)
from mcp_cronos.utils.markdown import extract_projects, parse_diary_file
from mcp_cronos.utils.projects import system_of


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

    # Riepilogo
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


def lista_progetti(
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 30,
    max_progetti: int = 100,
) -> dict:
    """
    Elenca i progetti menzionati nel diario in un periodo.

    Aggrega per nome canonico del progetto (tramite extract_projects, che
    applica la registry se presente), allega il sistema padre (system_of),
    raggruppa per sistema (per_sistema), restituisce prima e ultima data invece
    della lista completa, e limita l'output a max_progetti voci.

    Args:
        data_inizio: Data inizio in formato YYYY-MM-DD (opzionale)
        data_fine: Data fine in formato YYYY-MM-DD (opzionale)
        ultimi_giorni: Se non specificate le date, usa gli ultimi N giorni (default 30)
        max_progetti: Numero massimo di progetti restituiti, ordinati per frequenza
            decrescente (default 100). Se i progetti totali superano questo limite,
            troncato=True nel risultato.

    Returns:
        Dict con lista progetti canonici, rollup per sistema e flag di troncamento.
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

    # Raccogli progetti canonici e conteggi
    progetti_count: dict[str, int] = {}
    progetti_date: dict[str, list[str]] = {}

    for d in dates_to_read:
        file_path = get_file_path(d)
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            for proj in extract_projects(content):
                progetti_count[proj] = progetti_count.get(proj, 0) + 1
                progetti_date.setdefault(proj, []).append(str(d))

    ordinati = sorted(progetti_count.items(), key=lambda kv: kv[1], reverse=True)
    troncato = len(ordinati) > max_progetti
    progetti = []
    per_sistema: dict[str, int] = {}
    for nome, occ in ordinati[:max_progetti]:
        date_list = sorted(progetti_date[nome])
        sistema = system_of(nome)
        progetti.append(
            {
                "nome": nome,
                "sistema": sistema,
                "occorrenze": occ,
                "prima_data": date_list[0],
                "ultima_data": date_list[-1],
            }
        )
        if sistema:
            per_sistema[sistema] = per_sistema.get(sistema, 0) + occ

    return {
        "periodo": {"da": str(start), "a": str(end), "giorni_analizzati": len(dates_to_read)},
        "totale_progetti": len(progetti_count),
        "max_progetti": max_progetti,
        "troncato": troncato,
        "per_sistema": per_sistema,
        "progetti": progetti,
    }
