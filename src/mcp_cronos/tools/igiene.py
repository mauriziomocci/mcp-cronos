"""Diary hygiene advisor: read-only scan that reports actionable problems.

Controllo di igiene del diario: segnala voci fuori registro aggregate, fence non chiuse,
giorni feriali mancanti e giornate non chiuse, con gravita' e suggerimento.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.config import load_config
from mcp_cronos.utils.dates import (
    get_date_range,
    get_file_path,
    get_fine_giornata_path,
    get_today,
    has_legacy_file,
    parse_date,
)
from mcp_cronos.utils.markdown import has_unclosed_fence
from mcp_cronos.utils.projects import canonical_projects
from mcp_cronos.utils.scan import iter_diary_days
from mcp_cronos.utils.workdays import is_working_day

_GRAVITA = {
    "fence_non_chiusa": "critico",
    "voci_non_mappate": "avviso",
    "giorno_lavorativo_mancante": "info",
    "chiusura_mancante": "info",
}

_SUGGERIMENTI = {
    "voci_non_mappate": (
        "Lancia cronos_audit_progetti per vederle raggruppate e decidere cosa aggiungere"
        " a [cronos.projects]."
    ),
    "fence_non_chiusa": (
        "Chiudi il blocco con una riga di soli backtick (```): finche' resta aperto, "
        "tutte le voci successive di quel giorno si fondono e spariscono dalle analitiche."
    ),
    "giorno_lavorativo_mancante": (
        "Se era una giornata di ferie/malattia ignora; altrimenti il giorno non e' tracciato."
    ),
    "chiusura_mancante": (
        "Giornata aperta e mai chiusa: usa cronos_scrivi_fine_giornata per chiuderla."
    ),
}

_ORDINE_GRAVITA = {"critico": 0, "avviso": 1, "info": 2}


def _problema(tipo: str, d, dettaglio: str) -> dict:
    """Costruisce un dizionario problema con tipo, gravita', data, dettaglio e suggerimento."""
    return {
        "tipo": tipo,
        "gravita": _GRAVITA[tipo],
        "data": str(d),
        "dettaglio": dettaglio,
        "suggerimento": _SUGGERIMENTI[tipo],
    }


def _riepilogo(
    totale: int, conteggi_gravita: dict, conteggi: dict, nm_voci: int, nm_giorni: int
) -> str:
    """Genera una stringa di riepilogo leggibile per l'utente."""
    if totale == 0:
        return "Nessun problema rilevato nel periodo."
    c = conteggi_gravita["critico"]
    a = conteggi_gravita["avviso"]
    sev = (
        f"{c} {'critico' if c == 1 else 'critici'}, "
        f"{a} {'avviso' if a == 1 else 'avvisi'}, "
        f"{conteggi_gravita['info']} info"
    )
    frammenti = []

    # fence_non_chiusa (critico)
    n = conteggi["fence_non_chiusa"]
    if n:
        frammenti.append(f"{n} {'fence aperta' if n == 1 else 'fence aperte'}")

    # voci_non_mappate (avviso) — usa i contatori originali per la descrizione
    if nm_voci > 0:
        voce = "voce" if nm_voci == 1 else "voci"
        giorno = "giorno" if nm_giorni == 1 else "giorni"
        frammenti.append(f"{nm_voci} {voce} fuori registro (in {nm_giorni} {giorno})")

    # giorno_lavorativo_mancante (info)
    n = conteggi["giorno_lavorativo_mancante"]
    if n:
        frammenti.append(
            f"{n} {'giorno feriale senza diario' if n == 1 else 'giorni feriali senza diario'}"
        )

    # chiusura_mancante (info)
    n = conteggi["chiusura_mancante"]
    if n:
        frammenti.append(f"{n} {'giornata non chiusa' if n == 1 else 'giornate non chiuse'}")

    coda = " — " + ", ".join(frammenti) if frammenti else ""
    plur_prob = "problema" if totale == 1 else "problemi"
    return f"{totale} {plur_prob}: {sev}{coda}."


def igiene_diario(
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 180,
    max_problemi: int = 100,
) -> dict:
    """Scansione di igiene del diario: segnala problemi con gravita' e suggerimento.

    Modalita' sola lettura. Quattro check:
    - fence_non_chiusa: blocco di codice lasciato aperto (gravita' critico);
    - voci_non_mappate: finding aggregato — N voci in M giorni non mappano al registro (avviso);
    - giorno_lavorativo_mancante: giorno feriale senza file diario (info);
    - chiusura_mancante: giorno aperto (raw.md) ma senza fine-giornata.md (info).

    Il check voci_non_mappate produce un unico finding aggregato (non uno per voce)
    con i campi voci (conteggio), giorni (giorni distinti) e esempi (fino a 5 intestazioni).
    Per il dettaglio raggruppato per progetto usa cronos_audit_progetti.

    Risoluzione periodo: se data_inizio e data_fine sono entrambi presenti
    sovrascrivono ultimi_giorni; altrimenti la finestra e' [oggi - (ultimi_giorni-1), oggi].

    Args:
        data_inizio: Data inizio nel formato YYYY-MM-DD (opzionale).
        data_fine: Data fine nel formato YYYY-MM-DD (opzionale).
        ultimi_giorni: Giorni da analizzare se non fornita la finestra esplicita.
        max_problemi: Numero massimo di problemi restituiti (i conteggi restano totali).

    Returns:
        Dizionario con periodo, registro_attivo, riepilogo, problemi, conteggi,
        conteggi_gravita, totale_problemi, max_problemi, troncato, note.
    """
    if max_problemi < 0:
        max_problemi = 0

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

    config = load_config()
    registro_attivo = config.projects_registered
    problemi: list[dict] = []
    note: list[str] = []

    # Accumulatori per il finding aggregato voci_non_mappate
    nm_voci = 0
    nm_giorni: set[str] = set()
    nm_esempi: list[str] = []

    # Pass 1: giorni con file (scanner): fence, voci non mappate (accumulate), chiusura mancante
    for d, content, entries in iter_diary_days(start, end):
        if has_unclosed_fence(content):
            problemi.append(_problema("fence_non_chiusa", d, "blocco di codice aperto a fine file"))
        if registro_attivo:
            for heading, _body in entries:
                if not canonical_projects(heading):
                    nm_voci += 1
                    nm_giorni.add(str(d))
                    if len(nm_esempi) < 5:
                        nm_esempi.append(heading[:120])
        if not has_legacy_file(d) and not get_fine_giornata_path(d).exists():
            problemi.append(
                _problema("chiusura_mancante", d, "raw.md presente, fine-giornata.md assente")
            )

    # Pass 2: giorni lavorativi senza alcun file (festivo-aware)
    for d in get_date_range(start, end):
        if is_working_day(d) and not get_file_path(d).exists():
            problemi.append(
                _problema("giorno_lavorativo_mancante", d, "giorno lavorativo senza diario")
            )

    if not registro_attivo:
        note.append("registro vuoto: check voci_non_mappate saltato")

    # Appende il finding aggregato voci_non_mappate (dopo pass 2, dopo la nota registro vuoto)
    if registro_attivo and nm_voci > 0:
        problemi.append(
            {
                "tipo": "voci_non_mappate",
                "gravita": "avviso",
                "data": None,
                "dettaglio": (
                    f"{nm_voci} voci in {len(nm_giorni)} giorni non mappano ad alcun "
                    "progetto del registro"
                ),
                "suggerimento": _SUGGERIMENTI["voci_non_mappate"],
                "voci": nm_voci,
                "giorni": len(nm_giorni),
                "esempi": nm_esempi,
            }
        )

    conteggi = {t: 0 for t in _GRAVITA}
    conteggi_gravita: dict[str, int] = {"critico": 0, "avviso": 0, "info": 0}
    for p in problemi:
        conteggi[p["tipo"]] += 1
        conteggi_gravita[p["gravita"]] += 1
    totale = len(problemi)

    # Ordinamento: tollerare data=None (voci_non_mappate)
    problemi.sort(key=lambda p: (_ORDINE_GRAVITA[p["gravita"]], p.get("data") or ""))
    troncato = totale > max_problemi
    problemi_out = problemi[:max_problemi]

    return {
        "periodo": {"da": str(start), "a": str(end), "giorni_analizzati": (end - start).days + 1},
        "registro_attivo": registro_attivo,
        "riepilogo": _riepilogo(totale, conteggi_gravita, conteggi, nm_voci, len(nm_giorni)),
        "problemi": problemi_out,
        "conteggi": conteggi,
        "conteggi_gravita": conteggi_gravita,
        "totale_problemi": totale,
        "max_problemi": max_problemi,
        "troncato": troncato,
        "note": note,
    }
