"""
Tool per la generazione di riassunti discorsivi per lo standup.

Legge il diario e restituisce il contenuto completo delle entry
insieme a istruzioni di stile per la generazione del messaggio.
Il riassunto finale viene generato dall'LLM, non programmaticamente.

Stile del messaggio:
- Fluido e naturale, frasi discorsive, no elenchi puntati
- Molto alto livello, niente dettagli implementativi
- Niente numeri di MR/Jira, nomi di file, strumenti interni
- Dettagli tecnici solo se interessanti per decisioni future
"""

from datetime import date, timedelta
from typing import Optional

from mcp_cronos.utils.dates import get_file_path, get_today, parse_date, get_date_range
from mcp_cronos.utils.markdown import parse_diary_file


STILE_RIASSUNTO = """
ISTRUZIONI PER LA GENERAZIONE DEL RIASSUNTO:

Genera un messaggio discorsivo per lo standup o da inviare su Slack.
Deve sembrare scritto da una persona, non da un'AI.

REGOLE:
- Scritto in prima persona, tono naturale e colloquiale
- Continuità discorsiva assoluta: un flusso di frasi che scorrono l'una nell'altra,
  MAI elenchi puntati, MAI strutture rigide con grassetto per progetto
- Alto livello — racconta cosa hai fatto e perché, non come
- Niente dettagli implementativi (niente nomi file, classi, funzioni, MR, Jira)
- Niente strumenti interni (MCP, tool CLI, script, automazioni)
- Dettagli tecnici solo se servono a far capire il contesto o sono interessanti
  per decisioni future
- Se ci sono più progetti, collegali con transizioni naturali
  ("Finito quello...", "Nel pomeriggio...", "Sul fronte supporto...")
- Menziona le persone coinvolte quando rilevante
- Niente convenevoli, firme, saluti finali
- Se ci sono bloccanti, menzionali alla fine in modo naturale
- ATTENZIONE MASSIMA ad accenti e spaziature: usare sempre gli accenti
  corretti (è, à, ò, ù, perché, cioè, può, già, più, ecc.), MAI apostrofi
  al posto degli accenti (e' NO, è SI). Niente spazi mancanti o doppi,
  punteggiatura italiana corretta. Rileggere il testo prima di produrlo.

ESEMPIO DI TONO (messaggio reale inviato su Slack):
"Ieri ho lavorato tutto il giorno su IoPollicino. La mattina ho chiuso la feature
del codice referral facoltativo, mettendo il backend su stage presto così Matteo
poteva procedere in parallelo, e nel pomeriggio ho completato la parte dashboard
con le nuove metriche, i filtri per tipo utente e un warning che avvisa che siccome
gli utenti con referral code non compilano il questionario sull'app mentre gli altri
sì, le statistiche potrebbero essere sbilanciate verso gli utenti non-referral. La
situazione si normalizzerà quando verranno importati i dati dei questionari degli
utenti referral, ma nel frattempo il warning avvisa di leggere i numeri con cautela.
Finito quello, ho iniziato la nuova lavorazione sulle metriche della landing page.
Riccardo mi ha informato su quali statistiche servono — mezzo prevalente,
distribuzione modalità, motivo prevalente e tipo di mobilità attiva/motorizzata,
entro stamattina dovrei terminare."

COSA EVITARE:
- Elenchi puntati (MAI)
- Strutture con **Progetto** in grassetto seguite da descrizione
- Dettagli di implementazione
- Linguaggio burocratico
- Convenevoli e formule di cortesia
- Riferimenti a strumenti interni o automazioni
""".strip()


def genera_riassunto_standup(
    data: Optional[str] = None,
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
) -> dict:
    """
    Prepara i dati per generare un riassunto discorsivo per lo stand-up.

    Legge il diario per le date specificate e restituisce il contenuto
    completo delle entry insieme alle istruzioni di stile. Il riassunto
    viene generato dall'LLM sulla base di questi dati.

    Args:
        data: Data singola in formato YYYY-MM-DD (default: ultimo giorno lavorativo)
        data_inizio: Data inizio range in formato YYYY-MM-DD
        data_fine: Data fine range in formato YYYY-MM-DD

    Returns:
        Dict con contenuto del diario, istruzioni di stile e metadati
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
    else:
        # Default: ultimo giorno lavorativo
        dates_to_read = [_ultimo_giorno_lavorativo(today)]

    # Raccogli le entry con contenuto completo
    all_entries = []
    files_letti = []
    bloccanti = "Nessuno"

    for d in dates_to_read:
        file_path = get_file_path(d)
        if file_path.exists():
            diary = parse_diary_file(file_path)
            if diary:
                files_letti.append(str(d))
                bloccanti = diary.bloccanti
                for entry in diary.entries:
                    all_entries.append({
                        "data": str(d),
                        "progetto": entry.progetto,
                        "descrizione": entry.descrizione,
                        "contenuto_completo": entry.contenuto,
                        "richiesto_da": entry.richiesto_da,
                    })

    if not all_entries:
        return {
            "errore": "Nessuna entry trovata nel periodo specificato",
            "date_cercate": [str(d) for d in dates_to_read],
            "suggerimento": "Verifica che esistano file del diario per le date specificate"
        }

    # Determina il contesto temporale per il riassunto
    contesto = _determina_contesto_temporale(dates_to_read, today)

    return {
        "istruzioni_stile": STILE_RIASSUNTO,
        "contesto": contesto,
        "entries": all_entries,
        "bloccanti": bloccanti,
        "periodo": {
            "da": str(dates_to_read[0]),
            "a": str(dates_to_read[-1])
        },
        "files_letti": files_letti,
        "num_entries": len(all_entries),
        "progetti": list(dict.fromkeys(e["progetto"] for e in all_entries)),
    }


def _ultimo_giorno_lavorativo(oggi: date) -> date:
    """
    Calcola l'ultimo giorno lavorativo (lun-ven) prima di oggi.

    Args:
        oggi: Data odierna

    Returns:
        Data dell'ultimo giorno lavorativo
    """
    giorno = oggi - timedelta(days=1)
    # Sabato (5) -> venerdi, Domenica (6) -> venerdi
    while giorno.weekday() >= 5:
        giorno -= timedelta(days=1)
    return giorno


def _determina_contesto_temporale(dates: list[date], oggi: date) -> str:
    """
    Genera una descrizione del contesto temporale per il riassunto.

    Args:
        dates: Date coperte dal riassunto
        oggi: Data odierna

    Returns:
        Stringa descrittiva (es. "Ieri (venerdi 6 marzo)")
    """
    GIORNI_SETTIMANA = [
        "lunedi", "martedi", "mercoledi", "giovedi",
        "venerdi", "sabato", "domenica"
    ]
    MESI = [
        "gennaio", "febbraio", "marzo", "aprile",
        "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"
    ]

    if len(dates) == 1:
        d = dates[0]
        diff = (oggi - d).days
        giorno_sett = GIORNI_SETTIMANA[d.weekday()]
        mese = MESI[d.month - 1]

        if diff == 1:
            return f"Ieri ({giorno_sett} {d.day} {mese})"
        elif diff == 2:
            return f"L'altro ieri ({giorno_sett} {d.day} {mese})"
        elif diff <= 4:
            return f"{giorno_sett.capitalize()} scorso ({d.day} {mese})"
        else:
            return f"{giorno_sett.capitalize()} {d.day} {mese}"
    else:
        d_inizio = dates[0]
        d_fine = dates[-1]
        mese_inizio = MESI[d_inizio.month - 1]
        mese_fine = MESI[d_fine.month - 1]

        if d_inizio.month == d_fine.month:
            return f"Dal {d_inizio.day} al {d_fine.day} {mese_fine}"
        else:
            return f"Dal {d_inizio.day} {mese_inizio} al {d_fine.day} {mese_fine}"