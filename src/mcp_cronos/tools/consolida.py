"""
Tool per il consolidamento del diario.

Rilegge il file del diario, identifica le sezioni logiche e restituisce
il contenuto completo con istruzioni per l'LLM su come riscriverlo
eliminando ripetizioni, unificando entry che trattano lo stesso argomento,
e organizzando il tutto in modo coerente e logico.

Utile quando il diario e' stato scritto durante la giornata con entry
separate che andrebbero unificate, o quando contiene ripetizioni dovute
ad aggiornamenti successivi sullo stesso tema.
"""

from typing import Optional

from mcp_cronos.utils.dates import get_file_path, get_today, parse_date, get_standup_title


STILE_CONSOLIDAMENTO = """
ISTRUZIONI PER IL CONSOLIDAMENTO DEL DIARIO:

Hai ricevuto il contenuto completo del diario di oggi. Il file potrebbe contenere:
- Entry separate che trattano lo stesso argomento (es. analisi iniziale + approfondimento + verifica)
- Ripetizioni di dati e conclusioni tra entry diverse
- Informazioni sparse che andrebbero raggruppate
- Sezioni aggiunte in momenti diversi senza coerenza complessiva

Il tuo compito e' riscrivere il file consolidando tutto in modo coerente.

=== REGOLE DI CONSOLIDAMENTO ===

1. RAGGRUPPA PER PROGETTO E TEMA: entry diverse sullo stesso argomento vanno fuse in una
   singola sezione. Ad esempio, "analisi ticket X", "approfondimento ticket X",
   "verifica evidenze ticket X" diventano un'unica sezione "Ticket X" con la storia
   completa dall'inizio alla fine.

2. ELIMINA RIPETIZIONI: se lo stesso dato, conclusione o evidenza appare in piu' entry,
   tienilo una sola volta nel punto piu' logico.

3. MANTIENI TUTTI I DATI: non perdere informazioni. Se un'entry contiene un URL, un ID,
   una query, un riferimento tecnico, deve restare nel file consolidato.

4. ORDINE CRONOLOGICO E LOGICO: organizza le sezioni seguendo il flusso della giornata.
   Dentro ogni sezione, racconta la storia dall'inizio alla fine, non in ordine di
   quando le entry sono state scritte.

5. FORMATO:
   - Un H3 (###) per ogni progetto/tema principale
   - Testo discorsivo, non elenchi puntati infiniti
   - Sezioni "Dove verificare" con URL e query raggruppate alla fine della sezione
   - Riferimenti (repository, branch, Jira, MR) alla fine della sezione
   - Separatore --- tra sezioni di progetti diversi

6. NON AGGIUNGERE CONTENUTO: non inventare, non interpretare, non aggiungere
   conclusioni che non erano nel diario originale. Solo riorganizzare.

7. PRESERVA LE SEZIONI DI CHIUSURA: se il diario ha gia' un "Riassunto della giornata",
   "Riassunto tecnico", "Messaggio per lo standup", lasciali invariati.
   Se non li ha, non aggiungerli (per quelli c'e' il tool di fine giornata).

8. SEZIONE BLOCCANTI: mantienila sempre alla fine.

=== PROCEDURA ===

1. Leggi tutto il contenuto
2. Identifica i temi/progetti trattati
3. Per ogni tema, raccogli tutte le informazioni sparse nel file
4. Riscrivi ogni tema come una sezione unica, coerente e completa
5. Scrivi il file consolidato al path indicato nel campo `file`
""".strip()


def consolida_diario(
    data: Optional[str] = None,
) -> dict:
    """
    Rilegge il diario e restituisce il contenuto con istruzioni per consolidarlo.

    Il tool non modifica il file direttamente. Restituisce il contenuto completo
    e le istruzioni per l'LLM, che dovra' riscrivere il file eliminando
    ripetizioni e organizzando le sezioni in modo logico.

    Args:
        data: Data del diario in formato YYYY-MM-DD (default: oggi)

    Returns:
        Dict con contenuto del file, istruzioni e metadati
    """
    if data:
        try:
            file_date = parse_date(data)
        except ValueError as e:
            return {"errore": str(e)}
    else:
        file_date = get_today()

    file_path = get_file_path(file_date)

    if not file_path.exists():
        return {
            "errore": f"File non trovato per data {file_date}",
            "file": str(file_path),
        }

    contenuto = file_path.read_text(encoding="utf-8")

    if not contenuto.strip():
        return {
            "errore": f"File vuoto per data {file_date}",
            "file": str(file_path),
        }

    # Analisi del contenuto per identificare potenziali problemi
    lines = contenuto.split("\n")
    h3_sections = [l.strip() for l in lines if l.strip().startswith("### ")]
    h2_sections = [l.strip() for l in lines if l.strip().startswith("## ")]

    # Identifica progetti dai titoli H3
    progetti = []
    for h3 in h3_sections:
        header = h3[4:].strip()
        progetto = header.split(" - ")[0].split(" — ")[0].strip()
        progetti.append(progetto)

    # Conta occorrenze per progetto per identificare duplicati
    from collections import Counter
    progetto_count = Counter(progetti)
    duplicati = {p: c for p, c in progetto_count.items() if c > 1}

    # Calcola dimensione file
    num_righe = len(lines)
    num_sezioni_h3 = len(h3_sections)

    return {
        "istruzioni": STILE_CONSOLIDAMENTO,
        "data": str(file_date),
        "file": str(file_path),
        "titolo_standup": get_standup_title(file_date),
        "contenuto_completo": contenuto,
        "analisi": {
            "num_righe": num_righe,
            "num_sezioni_h3": num_sezioni_h3,
            "sezioni_h2": h2_sections,
            "sezioni_h3": h3_sections,
            "progetti_trovati": list(progetto_count.keys()),
            "progetti_con_entry_multiple": duplicati if duplicati else None,
        },
        "suggerimenti": _genera_suggerimenti(duplicati, num_sezioni_h3, h3_sections),
    }


def _genera_suggerimenti(duplicati: dict, num_sezioni: int, sezioni: list) -> list:
    """Genera suggerimenti per il consolidamento basati sull'analisi."""
    suggerimenti = []

    if duplicati:
        for progetto, count in duplicati.items():
            suggerimenti.append(
                f"Il progetto '{progetto}' ha {count} sezioni separate — "
                f"probabilmente vanno unificate in una sola"
            )

    if num_sezioni > 8:
        suggerimenti.append(
            f"Il diario ha {num_sezioni} sezioni H3 — valuta se alcune "
            f"possono essere raggruppate per tema"
        )

    # Cerca pattern di entry incrementali (analisi, approfondimento, verifica)
    incrementali = ["approfondimento", "verifica", "aggiornamento", "follow-up",
                     "correzione", "conferma", "dettaglio"]
    for sez in sezioni:
        sez_lower = sez.lower()
        for pattern in incrementali:
            if pattern in sez_lower:
                suggerimenti.append(
                    f"La sezione '{sez[4:]}' sembra un aggiornamento di una "
                    f"sezione precedente — valuta se integrarla"
                )
                break

    if not suggerimenti:
        suggerimenti.append("Nessun problema evidente rilevato nel formato")

    return suggerimenti
