"""
Tool per la ricerca full-text nel diario.

Cerca un pattern testuale nei file del diario (raw, todo, chiusura) e
restituisce i match con data, sorgente e contesto.

Sorgenti di ricerca (parametro `tipo`):
- "raw": entry del log giornaliero (granularita' per entry, default sempre incluso)
- "todo": file todo.md (lista cose da fare per la giornata)
- "chiusura": file fine-giornata.md (chiusura snella con decisioni, Q&A, ecc.)

Per "raw" la ricerca opera al livello dell'entry (progetto/descrizione/contenuto)
mantenendo la granularita' storica. Per "todo" e "chiusura" la ricerca e'
testuale full-file con un riquadro di contesto attorno al match.
"""

import re
from datetime import date as date_cls
from datetime import timedelta
from pathlib import Path
from typing import Optional

from mcp_cronos.utils.dates import (
    get_date_range,
    get_file_path,
    get_fine_giornata_path,
    get_today,
    get_todo_path,
    has_legacy_file,
    parse_date,
)
from mcp_cronos.utils.markdown import parse_diary_file

_SORGENTI_VALIDE = ("raw", "todo", "chiusura")


def cerca_nel_diario(
    query: str,
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 90,
    tipo: Optional[list[str]] = None,
    max_risultati: int = 50,
) -> dict:
    """
    Cerca un pattern testuale nei file del diario.

    Args:
        query: Testo da cercare (case-insensitive, supporta regex).
        data_inizio: Data inizio range YYYY-MM-DD.
        data_fine: Data fine range YYYY-MM-DD.
        ultimi_giorni: Giorni da cercare se non specificate le date (default 90).
        tipo: Lista di sorgenti da cercare fra "raw", "todo", "chiusura".
              Default: tutte e tre.
        max_risultati: Numero massimo di risultati restituiti (default 50).
            La ricerca trova tutti i match ma ne restituisce al piu' questo
            numero; il totale trovato resta in `totale_risultati`.

    Returns:
        Dict con risultati della ricerca, ciascuno marcato col `tipo` di
        sorgente che ha matchato.
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

    sorgenti = list(tipo) if tipo else list(_SORGENTI_VALIDE)
    invalidi = [t for t in sorgenti if t not in _SORGENTI_VALIDE]
    if invalidi:
        return {"errore": (f"Sorgenti non valide: {invalidi}. Ammesse: {list(_SORGENTI_VALIDE)}")}

    dates_to_search = get_date_range(start, end)

    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error as e:
        return {"errore": f"Pattern regex non valido: {e}"}

    risultati: list[dict] = []
    files_cercati = 0

    for d in dates_to_search:
        if "raw" in sorgenti:
            files_cercati += _cerca_raw(d, pattern, risultati)
        # todo e chiusura esistono solo nel nuovo layout: skip se la data
        # ha ancora il legacy single-file (li' tutto sta in raw).
        if not has_legacy_file(d):
            if "todo" in sorgenti:
                files_cercati += _cerca_file_libero(get_todo_path(d), d, "todo", pattern, risultati)
            if "chiusura" in sorgenti:
                files_cercati += _cerca_file_libero(
                    get_fine_giornata_path(d), d, "chiusura", pattern, risultati
                )

    max_risultati = max(0, max_risultati)
    troncato = len(risultati) > max_risultati
    output: dict = {
        "query": query,
        "periodo": {"da": str(start), "a": str(end)},
        "tipo": sorgenti,
        "files_cercati": files_cercati,
        "totale_risultati": len(risultati),
        "max_risultati": max_risultati,
        "troncato": troncato,
        "risultati": risultati[:max_risultati],
    }
    if troncato:
        output["nota"] = (
            f"Trovati {len(risultati)} match, mostrati i primi {max_risultati}. "
            "Restringi il range di date, usa 'tipo' per filtrare le sorgenti, "
            "o aumenta 'max_risultati'."
        )
    return output


def _cerca_raw(d: date_cls, pattern: re.Pattern, risultati: list[dict]) -> int:
    """Cerca nelle entry strutturate del raw.md (o legacy). Ritorna 1 se file letto."""
    file_path = get_file_path(d)
    if not file_path.exists():
        return 0
    diary = parse_diary_file(file_path)
    if not diary:
        return 1

    for entry in diary.entries:
        testo_completo = f"{entry.progetto} {entry.descrizione} {entry.contenuto}"
        matches = pattern.findall(testo_completo)
        if not matches:
            continue
        match_obj = pattern.search(testo_completo)
        contesto = _ritaglia_contesto(testo_completo, match_obj) if match_obj else ""
        risultati.append(
            {
                "tipo": "raw",
                "data": str(d),
                "progetto": entry.progetto,
                "descrizione": entry.descrizione,
                "num_match": len(matches),
                "contesto": contesto,
                "richiesto_da": entry.richiesto_da,
            }
        )
    return 1


def _cerca_file_libero(
    file_path: Path,
    d: date_cls,
    tipo_sorgente: str,
    pattern: re.Pattern,
    risultati: list[dict],
) -> int:
    """Cerca testualmente in un file libero (todo.md o fine-giornata.md). Ritorna 1 se file letto."""
    if not file_path.exists():
        return 0
    contenuto = file_path.read_text(encoding="utf-8")
    matches = pattern.findall(contenuto)
    if not matches:
        return 1
    match_obj = pattern.search(contenuto)
    contesto = _ritaglia_contesto(contenuto, match_obj) if match_obj else ""
    risultati.append(
        {
            "tipo": tipo_sorgente,
            "data": str(d),
            "file": str(file_path),
            "num_match": len(matches),
            "contesto": contesto,
        }
    )
    return 1


def _ritaglia_contesto(testo: str, match_obj: re.Match, padding: int = 100) -> str:
    """Estrae il testo intorno al primo match con un riquadro di `padding` caratteri."""
    start_ctx = max(0, match_obj.start() - padding)
    end_ctx = min(len(testo), match_obj.end() + padding)
    contesto = testo[start_ctx:end_ctx]
    if start_ctx > 0:
        contesto = "..." + contesto
    if end_ctx < len(testo):
        contesto = contesto + "..."
    return contesto
