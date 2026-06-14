# Sotto-progetto C2-C4 — Comodita' del workflow giornaliero

Data: 2026-06-14
Stato: Design (in attesa di review)
Roadmap: A, B, C1 fatte. Questo copre C2 (auto-detect git), C3 (default piu' snelli), C4 (chiusura serale unica). Resta D.

Tre feature piccole e coese, sullo stesso branch, ognuna con i suoi task e le sue review.

## C2 — Auto-rilevamento git (repository e branch)

### Problema
Aggiungendo una entry (`cronos_aggiungi_entry`, `cronos_aggiungi_a_progetto`) l'utente
digita a mano `repository` e `branch`. Sono dati che git gia' conosce.

### Design
Nuovo modulo `src/mcp_cronos/utils/gitinfo.py` con
`detect_git_info(working_dir: Optional[str] = None) -> tuple[Optional[str], Optional[str]]`:
- esegue `git -C <dir> rev-parse --show-toplevel` (il nome repo e' il basename del path)
  e `git -C <dir> rev-parse --abbrev-ref HEAD` (branch corrente);
- `<dir>` e' `working_dir` se fornito, altrimenti `os.getcwd()`;
- su qualunque errore (non e' un repo git, git assente, comando fallito) restituisce
  `(None, None)` senza sollevare. Cattura `FileNotFoundError` e
  `subprocess.CalledProcessError`, mai un bare `except`.

Integrazione in `aggiungi_entry` e `aggiungi_a_progetto`: nuovo parametro opzionale
`working_dir: Optional[str] = None`. Quando `repository` non e' fornito, lo riempie dal
rilevamento; idem per `branch`. I valori espliciti passati dall'utente vincono sempre sul
rilevamento. Aggiornare `inputSchema` e dispatch in `server.py` per entrambi i tool con il
nuovo parametro.

### Limite dichiarato (verita', non assunzione)
Il rilevamento usa la directory di lavoro del processo server MCP (o il `working_dir`
esplicito). Aiuta solo quando quella directory e' il repo di codice su cui l'utente sta
lavorando, il che dipende da come il client lancia il server MCP. Quando il server gira
altrove (es. nella cartella del diario o nella home), il rilevamento restituira'
`(None, None)` e il comportamento resta identico a oggi (campi vuoti). Il parametro
`working_dir` permette di puntare esplicitamente al repo quando serve. Non si promette
magia: si offre un riempimento best-effort piu' un override esplicito.

### Accettazione
Con un repo git temporaneo come `working_dir`, una entry senza `repository`/`branch`
viene salvata con repo = basename del repo e branch = branch corrente. Con `repository`
esplicito, il valore esplicito vince. In una directory non-git, nessun riferimento git e
nessun errore.

## C3 — Default piu' snelli

### Problema
`aggiungi_entry` ha tre campi obbligatori: `progetto`, `descrizione`, `paragrafo_intro`.
Il terzo e' spesso ridondante rispetto alla descrizione e aggiunge attrito.

### Design
Rendere `paragrafo_intro` opzionale (`paragrafo_intro: str = ""`), rimuovendolo dai
`required` dell'`inputSchema` in `server.py`. Quando e' vuoto, l'entry si renderizza senza
un paragrafo introduttivo vuoto: in `templates.py`, `Entry.to_markdown` deve appendere il
paragrafo introduttivo SOLO se non vuoto (oggi lo appende sempre, producendo una riga
vuota quando manca).

### Escluso di proposito (sicurezza)
NON si deduce automaticamente il `progetto` dall'ultima entry. Indovinare il progetto
rischia di attribuire il lavoro al progetto sbagliato e sporcare il diario in modo
silenzioso; il costo di un errore supera la comodita'. `progetto` e `descrizione` restano
obbligatori. Date e titoli sono gia' automatici (default oggi, titolo calcolato), quindi
non c'e' altro da fare li'.

### Accettazione
`aggiungi_entry` con solo `progetto` e `descrizione` (senza `paragrafo_intro`) crea
un'entry valida senza riga vuota spuria. Con `paragrafo_intro` fornito, l'output e'
identico a oggi.

## C4 — Chiusura serale in un comando

### Problema
La sera servono due chiamate di scrittura: `cronos_scrivi_fine_giornata` per la chiusura e
poi `cronos_prepara_domani` per impostare il giorno dopo.

### Design
Estendere `cronos_scrivi_fine_giornata` con un parametro opzionale
`contenuto_todo: Optional[str] = None`. Quando fornito, dopo aver scritto e committato il
file di chiusura, il tool chiama `prepara_domani(contenuto_todo)` (giorno target = prossimo
giorno lavorativo, ora festivo-aware grazie a C1) e include il suo risultato nella risposta
sotto una chiave `prepara_domani`. Quando `contenuto_todo` non e' fornito, il comportamento
e' identico a oggi (nessuna preparazione del domani). Aggiornare `inputSchema` e dispatch in
`server.py`.

Scelta: estendere il tool esistente invece di crearne uno nuovo mantiene basso il numero di
tool (coerente con l'obiettivo token della fase B) e il flusso serale diventa una singola
chiamata, retrocompatibile.

### Accettazione
`scrivi_fine_giornata(contenuto, contenuto_todo="...")` scrive la chiusura, fa il commit, e
prepara la cartella del prossimo giorno lavorativo con `todo.md`; la risposta contiene sia
l'esito della scrittura sia, sotto `prepara_domani`, i path creati. Senza `contenuto_todo`,
la risposta e il comportamento sono quelli attuali.

## Non-obiettivi
- Nessuna deduzione automatica del progetto (vedi C3).
- Nessun nuovo tool: C4 estende un tool esistente.
- Nessuna modifica al flusso a due fasi di `fine_giornata` (generazione LLM) oltre
  all'estensione di scrittura descritta.

## Strategia di test
Test-first per ogni feature.
- C2: test di `detect_git_info` con un repo git temporaneo (`git init`, commit, branch) ->
  (basename, branch); in dir non-git -> (None, None); `aggiungi_entry` riempie repo/branch
  dal rilevamento quando omessi e rispetta i valori espliciti.
- C3: `aggiungi_entry` senza `paragrafo_intro` -> entry valida, nessuna riga vuota spuria;
  `Entry.to_markdown` salta l'intro vuoto.
- C4: `scrivi_fine_giornata` con `contenuto_todo` -> scrive chiusura + prepara prossimo
  giorno lavorativo (mockare/usare git disabilitato via config nei test); senza, invariato.
- Suite completa verde, ruff pulito. README + CLAUDE.md aggiornati (nuovi parametri
  `working_dir`, `paragrafo_intro` opzionale, `contenuto_todo`).

## Rischi e compromessi
- **C2 dipende dalla cwd del server.** Dichiarato sopra; mitigato dal parametro
  `working_dir` e dal fallback silenzioso a nessun riferimento.
- **C4 accoppia chiusura e preparazione.** Resta opzionale: senza `contenuto_todo` il
  comportamento e' invariato, quindi nessuna regressione per chi vuole i due passi separati.
- **C2 esegue subprocess git.** Comandi a lista fissa (nessuna shell, nessuna
  interpolazione di input utente), `check=True` con cattura delle eccezioni: nessun rischio
  di injection.

## Fasi
Il piano (via writing-plans) sequenziera': C2 (gitinfo + integrazione), poi C3
(paragrafo_intro opzionale + render), poi C4 (estensione scrivi_fine_giornata), infine
aggiornamento README + CLAUDE.md.
