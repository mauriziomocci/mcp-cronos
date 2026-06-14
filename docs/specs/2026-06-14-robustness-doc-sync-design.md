# Sotto-progetto A — Robustezza e allineamento documentazione

Data: 2026-06-14
Stato: Design (in attesa di review)
Roadmap: A (questo) -> B (efficienza token/contesto) -> C (workflow giornaliero) -> D (nuove capacita')

## Problema

`mcp-cronos` e' un pacchetto maturo e pubblicato (PyPI v1.0.0) con una suite di
test ampia. Tre difetti concreti ne minano l'affidabilita' come base per il
lavoro di miglioramento successivo:

1. **Drift della documentazione.** `server.py` registra 14 tool. `CLAUDE.md`
   dichiara "11 tools" in due punti (righe 36 e 228), il suo albero di
   architettura omette `leggi_todo.py`, `lista_mese.py`, `prepara_domani.py`, e
   la sezione End-of-Day non cita mai `prepara_domani`. `README.md` documenta 12
   tool e omette del tutto `cronos_leggi_todo`, `cronos_lista_mese`,
   `cronos_prepara_domani`. La sezione `cronos_cerca` del README precede la
   ricerca multi-sorgente e non documenta il parametro `tipo`
   (`raw` / `todo` / `chiusura`). La sezione "Diary Format" del README descrive
   ancora il layout a file singolo, mentre il codice e' passato al layout
   cartella-per-giorno (`raw.md` + `fine-giornata.md` + `todo.md`), con il file
   singolo mantenuto solo per i giorni legacy.

2. **Bug i18n — etichette italiane hardcoded.** Due etichette del diario sono
   scritte come letterali italiani a prescindere dalla lingua configurata:
   `Riferimenti` (il blocco riferimenti) e `Richiesto da` (la riga del
   richiedente). Compaiono in tre moduli — `templates.py`,
   `tools/aggiungi_progetto.py`, `utils/markdown.py` — e vengono ri-parsate in
   `utils/markdown.py`. Con `lang = "en"` un utente inglese ottiene comunque
   "Riferimenti" e "Richiesto da". Le etichette sono assenti dal sistema i18n
   `LanguagePack.sections`.

3. **Fragilita' del parsing (da dimostrare prima di fixare).** `parse_entries`
   in `utils/markdown.py` splitta le entry con `re.split(r"\n(?=### )", content)`
   e individua i confini delle entry con controlli di prefisso di riga su
   `### `, `---` e `## `. Un blocco di codice fenced (```` ``` ````) dentro il
   contenuto di una entry che contenga una riga che inizia con `### ` o una riga
   `---` verrebbe letto come una nuova entry o come terminatore di entry. E'
   plausibile ma non ancora dimostrato; va confermato con un test che fallisce
   prima di qualsiasi modifica al parser.

## Obiettivi

- La documentazione (README, CLAUDE.md) riflette accuratamente i 14 tool, il
  layout cartella-per-giorno e il parametro `tipo` di `cerca`.
- Le etichette del diario `references` e `requested_by` rispettano la lingua
  configurata, mantenendo al contempo pienamente parsabili i file di diario
  esistenti con etichette italiane.
- Il parsing markdown e' robusto rispetto ai blocchi di codice fenced,
  verificato da test.

## Non-obiettivi

- Nessuna ottimizzazione token/contesto del flusso di fine giornata
  (sotto-progetto B).
- Nessun tool o capacita' nuova (sotto-progetto D).
- Nessun cambiamento al formato dei file di diario su disco oltre alla
  localizzazione delle etichette, che e' retrocompatibile (vedi sotto).
- Nessuna migrazione dei diari legacy a file singolo verso il layout a cartella.

## Design

### 1. Allineamento documentazione

Meccanico, basso rischio, fatto per ultimo cosi' documenta lo stato gia'
corretto.

- `CLAUDE.md`: correggere il conteggio dei tool (11 -> 14) in entrambe le
  occorrenze; aggiungere `leggi_todo.py`, `lista_mese.py`, `prepara_domani.py`
  all'albero di architettura con una descrizione di una riga; estendere la lista
  degli scope di commit con i nomi dei nuovi moduli; citare `prepara_domani`
  nel workflow di fine giornata come passo opzionale di preparazione del giorno
  successivo.
- `README.md`: aggiungere i tre tool mancanti sia alla sezione "Tools" inglese
  sia a quella italiana e agli elenchi puntati delle feature; documentare il
  parametro `tipo` di `cerca`; aggiornare la sezione "Diary Format" per
  descrivere il layout cartella-per-giorno (`{data}/raw.md`,
  `{data}/fine-giornata.md`, `{data}/todo.md`) e segnalare che i giorni legacy
  mantengono la forma a file singolo.

Criterio di accettazione: ogni tool registrato in `server.py` `TOOLS` compare in
entrambe le doc; nessuna doc fa riferimento a un conteggio di tool o a un layout
che contraddice il codice.

### 2. Localizzazione i18n delle etichette

Il difetto si estende su generazione (3 moduli) e parsing (1 modulo). Il fix
deve localizzare l'output mantenendo parsabili tutti i diari scritti in
precedenza.

**Memorizzazione etichette.** Aggiungere due chiavi a `LanguagePack.sections` in
entrambi i pacchetti: `references` ("Riferimenti" / "References") e
`requested_by` ("Richiesto da" / "Requested by"). Aggiornare la lista delle
chiavi documentate nel docstring di `LanguagePack`. Esporle entrambe su
`CronosConfig` (es. `section_references`, `section_requested_by`) in
`config.py`, con la risoluzione esistente override-utente + default-lingua +
fallback hardcoded.

**Generazione.** Sostituire i letterali hardcoded in `templates.py`,
`tools/aggiungi_progetto.py` e nel percorso di render di `utils/markdown.py`
(`render_entry`) con le etichette configurate.

**Parsing — retrocompatibilita' (critica).** `extract_references` e la regex
"Richiesto da" in `utils/markdown.py` oggi matchano il letterale italiano.
Devono matchare l'etichetta *configurata*, ma anche continuare a matchare i
default italiani cosi' che i diari scritti prima di questa modifica (tutti con
etichette italiane) restino parsabili quando un utente passa poi a `lang = "en"`.
Il parser accettera' quindi un piccolo insieme: l'etichetta configurata piu' il
default italiano integrato. Questo mantiene corretto il round-trip attraverso un
cambio di lingua ed evita una migrazione dati.

**Fuori scope per le etichette.** La sintassi del marcatore italico
`*-Richiesto da {nome}-*` e la sintassi bold `**{etichetta}:**` restano
invariate; si localizza solo il testo dell'etichetta. I template di prompt per
l'LLM (`default_templates/*.md`) supportano gia' l'override utente e non fanno
parte di questo fix.

Criterio di accettazione: con `lang = "en"`, una entry generata da zero mostra
"References" e "Requested by"; un file di diario italiano esistente continua a
parsare correttamente i suoi riferimenti e il richiedente sia con `lang = "it"`
sia con `lang = "en"`.

### 3. Parsing consapevole dei code-fence

Test-first. Prima di qualsiasi modifica a `parse_entries`:

1. Aggiungere test che costruiscano il contenuto di una entry contenente un
   blocco di codice fenced con una riga interna `### heading` e una riga `---`,
   poi asserire che il parser produca la singola entry attesa (non uno split
   spurio).
2. Se i test passano, la fragilita' non esiste in pratica: documentare questo
   esito nel file di test e fermarsi. Nessuna modifica al codice.
3. Se i test falliscono, rendere `parse_entries` (e i controlli di confine
   `---`/`## ` su cui si appoggia) consapevoli dei fence: tracciare se la riga
   corrente e' dentro un blocco fenced (toggle sulle righe la cui forma strippata
   inizia con ```` ``` ````) e ignorare i marker strutturali mentre si e' dentro
   un fence. Ri-eseguire fino al verde.

Criterio di accettazione: un test documentato dimostra il comportamento del
parser sul contenuto fenced; se e' servito un fix, il test prima fallito ora
passa e nessun test esistente regredisce.

## Strategia di test

- I nuovi test vivono accanto alla suite esistente sotto `tests/`.
- i18n: estendere `test_i18n.py` e `test_markdown.py` per coprire la generazione
  delle etichette e il fallback di parsing italiano-legacy sotto entrambe le
  lingue.
- Parsing: aggiungere casi di codice fenced a `test_markdown.py`.
- La suite completa deve restare verde (zero test falliti, regola di progetto).

## Rischi e compromessi

- **Insieme di fallback del parser.** Accettare sia l'etichetta configurata sia
  il default italiano e' un compromesso deliberato: preserva i dati esistenti al
  costo di una minima ambiguita' (un utente inglese che digiti letteralmente
  "Riferimenti" verrebbe comunque riconosciuto). Accettabile per un diario
  locale mono-utente.
- **Ordine doc-per-ultima.** Scrivere la documentazione dopo i fix rischia di
  far dimenticare un aggiornamento; mitigato dal criterio di accettazione
  esplicito che incrocia `server.py` con entrambe le doc.

## Fasi

Il piano di implementazione (passo successivo, via writing-plans) sequenziera' A
come: prima i test del parsing fence (prova/smentisce), poi il fix i18n delle
etichette, poi l'allineamento doc.
