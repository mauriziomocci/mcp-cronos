"""
Tool for listing the diary days of a given month.

Returns one row per day of the month with flags indicating which artifacts
are present: legacy single-file (storico), raw.md, todo.md, fine-giornata.md.
For raw/legacy files it also reports the number of parsed entries when
available.

Useful as an at-a-glance dashboard for the month: where you have closed
days, where todos are pending, which days are still empty.
"""

import calendar
from datetime import date
from typing import Optional

from mcp_cronos.utils.dates import (
    get_fine_giornata_path,
    get_legacy_file_path,
    get_raw_path,
    get_today,
    get_todo_path,
)
from mcp_cronos.utils.markdown import parse_diary_file


def lista_mese(
    mese: Optional[int] = None,
    anno: Optional[int] = None,
) -> dict:
    """
    Lista lo stato del diario per ogni giorno di un mese.

    Args:
        mese: Numero mese 1-12. Se omesso, usa il mese corrente.
        anno: Anno YYYY. Se omesso, usa l'anno corrente.

    Returns:
        Dict con riepilogo (totali) e una riga per ogni giorno del mese
        con flag presenza file e count entry.
    """
    today = get_today()
    target_anno = anno if anno is not None else today.year
    target_mese = mese if mese is not None else today.month

    if not (1 <= target_mese <= 12):
        return {"errore": f"Mese non valido: {target_mese}. Atteso 1-12."}

    _, num_giorni = calendar.monthrange(target_anno, target_mese)

    giorni = []
    tot_legacy = 0
    tot_raw = 0
    tot_todo = 0
    tot_chiusura = 0
    tot_entries = 0

    for giorno in range(1, num_giorni + 1):
        d = date(target_anno, target_mese, giorno)
        legacy_p = get_legacy_file_path(d)
        raw_p = get_raw_path(d)
        todo_p = get_todo_path(d)
        chiusura_p = get_fine_giornata_path(d)

        has_legacy = legacy_p.exists()
        has_raw = raw_p.exists()
        has_todo = todo_p.exists()
        has_chiusura = chiusura_p.exists()

        # Conteggio entry: parsing del file principale (legacy o raw)
        num_entries = 0
        if has_legacy:
            tot_legacy += 1
            diary = parse_diary_file(legacy_p)
            if diary:
                num_entries = len(diary.entries)
        elif has_raw:
            tot_raw += 1
            diary = parse_diary_file(raw_p)
            if diary:
                num_entries = len(diary.entries)
        if has_todo:
            tot_todo += 1
        if has_chiusura:
            tot_chiusura += 1
        tot_entries += num_entries

        giorni.append(
            {
                "data": str(d),
                "giorno_settimana": d.weekday(),  # 0=lun, 6=dom
                "legacy": has_legacy,
                "raw": has_raw,
                "todo": has_todo,
                "chiusura": has_chiusura,
                "num_entries": num_entries,
            }
        )

    return {
        "anno": target_anno,
        "mese": target_mese,
        "giorni_nel_mese": num_giorni,
        "riepilogo": {
            "giorni_legacy": tot_legacy,
            "giorni_raw": tot_raw,
            "giorni_con_todo": tot_todo,
            "giorni_con_chiusura": tot_chiusura,
            "totale_entries": tot_entries,
        },
        "giorni": giorni,
    }
