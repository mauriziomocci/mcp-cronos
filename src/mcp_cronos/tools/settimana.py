"""
Tool per il riassunto settimanale del diario.

Raggruppa il lavoro della settimana per progetto, mostrando
quanti giorni si e' lavorato su ciascuno e un riepilogo delle attivita'.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.utils.dates import get_date_range, get_file_path, get_today, parse_date
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
    progetti = {}
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
