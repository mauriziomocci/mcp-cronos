"""
Tool per la chiusura di fine giornata del diario.

Legge le entry grezze del giorno e restituisce istruzioni per:
1. Riscriverle in ordine cronologico/logico
2. Generare riassunto della giornata
3. Generare riassunto tecnico
4. Generare messaggio per lo standup

L'LLM genera i quattro output e scrive il file completo direttamente.
"""

from typing import Optional

from mcp_cronos.utils.dates import get_file_path, get_today, parse_date, get_standup_title
from mcp_cronos.utils.markdown import parse_diary_file


STILE_FINE_GIORNATA = """
ISTRUZIONI PER LA CHIUSURA DI FINE GIORNATA:

Hai ricevuto le entry grezze del diario di oggi. Devi produrre un file markdown
completo con CINQUE sezioni, poi scriverlo al path indicato in `file`.

=== STRUTTURA DEL FILE DA SCRIVERE ===

```
# {titolo_standup}

## Riassunto della giornata

{riassunto_giornata}

## Riassunto tecnico

{riassunto_tecnico}

---

## Messaggio per lo standup

{messaggio_standup}

---

## Cosa ho fatto ieri

{entries_riscritte}

---

## Bloccanti

{bloccanti}
```

=== SEZIONE 1: ENTRIES RISCRITTE ===

Riscrivi le entry in ordine cronologico e logico. Le entry originali potrebbero essere
state aggiunte a casaccio durante la giornata — il tuo compito è riordinarle e
ristrutturarle in un racconto coerente della giornata.

Formato:
- Un unico H3 per progetto: `### {Progetto} - {Descrizione generale della giornata su quel progetto}`
- Paragrafo introduttivo che riassume il lavoro complessivo sul progetto
- Sotto-sezioni H4 (`####`) per ogni fase/attività distinta, in ordine cronologico:
  `#### Fase 1 — {Titolo fase}`
- Dentro ogni fase: descrizione dettagliata con bullet points, blocchi codice se utili,
  nomi di file, commit, comandi, config — tutto ciò che serve a ricostruire cosa è stato fatto
- Sezione `**Riferimenti:**` alla fine dell'entry con repository, branch, Jira, MR
- Separatore `---` tra entry di progetti diversi

Livello di dettaglio: MASSIMO. Questo è il log tecnico completo della giornata.
Includi commit hash, nomi file, classi, configurazioni, comandi eseguiti, errori
incontrati e come sono stati risolti.

=== SEZIONE 2: RIASSUNTO DELLA GIORNATA ===

Un paragrafo unico, denso e fluido che racconta l'intera giornata. Scritto come
se stessi raccontando a un collega tecnico cosa hai fatto, in modo scorrevole
ma completo.

Stile:
- Un solo paragrafo continuo (può essere lungo)
- Segui l'ordine cronologico della giornata
- Menziona i progetti, cosa è stato fatto e perché
- Includi problemi incontrati e come sono stati risolti
- Livello medio-alto: abbastanza tecnico da capire COSA è stato fatto,
  senza entrare nel dettaglio di COME (niente nomi file, commit, config)
- Menziona ticket Jira e MR solo come riferimento generico ("ho creato i task Jira")
- Non usare elenchi puntati, solo prosa fluida

Esempio di tono (dal diario reale):
"Giornata interamente dedicata a Pollicino (RapsodiaTrace), proseguendo il lavoro
Keycloak del giorno precedente. La mattina è partita con un audit di tutti i README
del progetto per allinearli alle modifiche KC introdotte il giorno prima, seguito
dal merge di develop in master che era rimasto indietro di ~20 commit. Poi ho
affrontato l'analisi e implementazione di tre funzionalità KC avanzate..."

=== SEZIONE 3: RIASSUNTO TECNICO ===

Un riassunto estremamente denso e tecnico. Scritto per uno sviluppatore che deve
capire esattamente cosa è stato fatto, con tutti i dettagli implementativi.

Stile:
- Uno o due paragrafi densi (non elenchi puntati)
- Includi: commit hash, nomi file, classi, funzioni, configurazioni specifiche,
  versioni, comandi, flag, variabili d'ambiente, endpoint API
- Includi errori specifici incontrati (messaggi di errore, status code)
- Includi workaround e soluzioni tecniche precise
- Includi nomi di tool, librerie, framework con versioni
- Usa parentesi e trattini per compattare le informazioni
- Non spiegare il "perché" — solo il "cosa" e il "come"

Esempio di tono (dal diario reale):
"Audit e allineamento di 6 README (commit `08687a8`), merge develop in master
(`85920da`). Analisi e piano per 3 funzionalità KC: SMTP AWS SES con placeholder
`$(env:VAR)` risolti a runtime da config-cli (`IMPORT_VARSUBSTITUTION_ENABLED=true`),
flow custom `browser-dashboard-mfa` con doppio nesting..."

=== SEZIONE 4: MESSAGGIO PER LO STANDUP ===

Messaggio discorsivo che può essere usato sia per lo standup che inviato
direttamente su Slack a un collega. Deve sembrare scritto da una persona,
non da un'AI. Seguire queste regole:

- Scritto in prima persona, tono naturale e colloquiale
- Continuità discorsiva assoluta: un flusso di frasi che scorrono l'una nell'altra,
  MAI elenchi puntati, MAI strutture rigide con grassetto per progetto
- Alto livello — racconta cosa hai fatto e perché, non come
- Niente dettagli implementativi (niente nomi file, classi, funzioni, commit, MR, Jira)
- Niente strumenti interni (MCP, tool CLI, script, automazioni)
- Dettagli tecnici SOLO se servono a far capire il contesto o sono
  interessanti per decisioni future
- Niente convenevoli, niente firme, niente saluti finali
- Se ci sono più progetti, collegali con transizioni naturali
  ("Finito quello...", "Nel pomeriggio...", "Sul fronte supporto...")
- Se ci sono bloccanti, menzionali alla fine in modo naturale
- Menziona le persone coinvolte quando rilevante (chi ha chiesto, chi lavora in parallelo)
- ATTENZIONE MASSIMA ad accenti e spaziature: usare sempre gli accenti
  corretti (è, à, ò, ù, perché, cioè, può, già, più, ecc.), MAI apostrofi
  al posto degli accenti (e' NO, è SÌ). Niente spazi mancanti o doppi,
  punteggiatura italiana corretta. Rileggere il testo prima di produrlo.

Esempio di tono (messaggio reale inviato su Slack):
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

=== PROCEDURA ===

1. Leggi attentamente tutte le entry grezze
2. Identifica l'ordine cronologico e i raggruppamenti logici
3. Genera le cinque sezioni (entries riscritte, riassunto giornata, riassunto tecnico, messaggio standup, bloccanti)
4. Assembla il file markdown completo seguendo la struttura indicata sopra
5. Chiama cronos_scrivi_fine_giornata con il contenuto generato per scrivere il file
""".strip()


def fine_giornata(
    data: Optional[str] = None,
) -> dict:
    """
    Prepara i dati per la chiusura di fine giornata.

    Legge le entry del giorno e restituisce il contenuto completo
    insieme alle istruzioni di stile per generare i quattro output
    e scrivere il file definitivo.

    Args:
        data: Data del diario in formato YYYY-MM-DD (default: oggi)

    Returns:
        Dict con entries, istruzioni, path del file e metadati
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
            "suggerimento": "Usa cronos_aggiungi_entry per creare il file e aggiungere entry durante la giornata"
        }

    diary = parse_diary_file(file_path)
    contenuto_grezzo = file_path.read_text(encoding="utf-8")

    # Supporta sia il formato strutturato (con entry parsate)
    # sia il formato libero (consolidato manualmente, senza sezione
    # "Cosa ho fatto ieri" o entry con formato ### Progetto - Descrizione)
    if diary and diary.entries:
        # Raggruppa entry dello stesso progetto per evitare frammentazione
        entries = _consolida_entries(diary.entries)

        return {
            "istruzioni": STILE_FINE_GIORNATA,
            "data": str(file_date),
            "file": str(file_path),
            "titolo_standup": get_standup_title(file_date),
            "entries": entries,
            "bloccanti": diary.bloccanti if diary else "Nessuno",
            "num_entries": len(entries),
            "progetti": list(dict.fromkeys(e["progetto"] for e in entries)),
        }

    # Formato libero: il file esiste ma non ha entry parsabili.
    progetti = []
    bloccanti = "Nessuno"
    for line in contenuto_grezzo.split("\n"):
        stripped = line.strip()
        if stripped.startswith("### "):
            header = stripped[4:].strip()
            progetto = header.split(" - ")[0].split(" — ")[0].strip()
            if progetto and progetto not in progetti:
                progetti.append(progetto)
        if stripped == "## Bloccanti":
            idx = contenuto_grezzo.index("## Bloccanti")
            bloccanti_text = contenuto_grezzo[idx + len("## Bloccanti"):].strip()
            next_h2 = bloccanti_text.find("\n## ")
            if next_h2 > 0:
                bloccanti_text = bloccanti_text[:next_h2].strip()
            if bloccanti_text:
                bloccanti = bloccanti_text

    return {
        "istruzioni": STILE_FINE_GIORNATA,
        "data": str(file_date),
        "file": str(file_path),
        "titolo_standup": get_standup_title(file_date),
        "formato": "libero",
        "nota": (
            "Il diario non ha il formato standard con sezione "
            "'Cosa ho fatto ieri' e entry ### Progetto - Descrizione. "
            "Viene fornito il contenuto completo del file. "
            "Leggilo, identifica le sezioni logiche, e genera "
            "i quattro output di fine giornata."
        ),
        "contenuto_completo": contenuto_grezzo,
        "bloccanti": bloccanti,
        "progetti": progetti,
    }


def _consolida_entries(entries) -> list[dict]:
    """
    Raggruppa entry dello stesso progetto in un'unica entry consolidata.

    Se ci sono 3 entry per "Goceano", le unisce in una sola con il contenuto
    concatenato. Le descrizioni vengono combinate e il contenuto separato
    da sotto-sezioni.
    """
    progetti_visti = {}
    risultato = []

    for entry in entries:
        proj = entry.progetto
        entry_data = {
            "progetto": proj,
            "descrizione": entry.descrizione,
            "contenuto_completo": entry.contenuto,
            "richiesto_da": entry.richiesto_da,
        }

        if proj not in progetti_visti:
            progetti_visti[proj] = len(risultato)
            risultato.append(entry_data)
        else:
            # Progetto già visto: consolida
            idx = progetti_visti[proj]
            esistente = risultato[idx]

            # Combina descrizioni se diverse
            if entry.descrizione and entry.descrizione != esistente["descrizione"]:
                esistente["descrizione"] += f" / {entry.descrizione}"

            # Aggiungi contenuto come sotto-sezione
            separatore = f"\n\n--- entry successiva: {entry.descrizione} ---\n\n" if entry.descrizione else "\n\n"
            esistente["contenuto_completo"] += separatore + entry.contenuto

            # Preserva richiesto_da se non già presente
            if entry.richiesto_da and not esistente["richiesto_da"]:
                esistente["richiesto_da"] = entry.richiesto_da

    return risultato
