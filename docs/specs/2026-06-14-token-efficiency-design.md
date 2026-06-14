# Sotto-progetto B — Efficienza token/contesto

Data: 2026-06-14
Stato: Design (in attesa di review)
Roadmap: A (fatta) -> B (questo) -> C (workflow giornaliero) -> D (capacita' professionali)

## Problema

I tool di Cronos restituiscono dati che finiscono nel contesto dell'LLM. Due
punti, verificati leggendo il sorgente, producono output che cresce senza un
tetto e gonfia il contesto senza aggiungere valore proporzionale.

Il primo e' la ricerca. `cerca_nel_diario` in `src/mcp_cronos/tools/cerca.py`
itera su tutto il range (default 90 giorni) e su tre sorgenti (raw, todo,
chiusura) e accoda un risultato per ogni file/entry che matcha, senza alcun
limite. Ogni risultato porta una finestra di contesto di circa 200 caratteri
piu' i metadati. Su un diario con storia lunga una query frequente puo'
restituire decine di match: l'output cresce linearmente con la storia e con la
frequenza del termine, e nulla lo limita.

Il secondo e' la lettura su range. `leggi_diario` in
`src/mcp_cronos/tools/reader.py` emette, per ogni giorno MANCANTE nel periodo,
un oggetto-stub `{"data", "file", "esiste": False, "messaggio": "File non
trovato"}` dentro la lista `giorni`. Con `ultimi_giorni=30` su un diario sparso
si ottengono fino a 30 oggetti che non portano informazione utile oltre alla
data. Le entry reali sono gia' troncate a 200 caratteri (`contenuto_preview`),
quindi quelle non sono il problema: il grasso sono gli stub dei giorni vuoti.

## Obiettivi

- `cerca` ha un tetto configurabile sul numero di risultati restituiti, riporta
  in modo esplicito quando ha troncato e quanti match totali ha trovato, cosi'
  l'informazione "ce ne sono altri" non sparisce in silenzio.
- `leggi_diario` su range non emette piu' un oggetto per ogni giorno mancante:
  i giorni mancanti finiscono in una lista sintetica di date, e `giorni`
  contiene solo i giorni con contenuto reale.

## Non-obiettivi

- Nessuna modifica al flusso di fine giornata a due fasi (`fine_giornata` ->
  LLM -> `scrivi_fine_giornata`). E' architetturalmente necessario che l'LLM
  rigeneri il contenuto e lo rimandi al tool di scrittura; non si puo' evitare
  di far transitare quel testo nel contesto. Tagliare li' sarebbe alto rischio e
  basso guadagno.
- Nessuna modifica all'ottimizzazione gia' presente in `standup.py`, che riusa
  `fine-giornata.md` (discorso e Q&A) quando esiste invece di rigenerarlo.
- Nessun cambiamento al troncamento a 200 caratteri delle entry in
  `leggi_diario`, gia' compatto.
- Nessun tetto su `lista_progetti` / `settimana`: il loro output e' aggregato e
  gia' proporzionato (conteggi e date per progetto, non contenuto grezzo).

## Design

### 1. Tetto sui risultati di `cerca`

Aggiungere un parametro `max_risultati: int = 50` a `cerca_nel_diario` e alla
definizione del tool in `server.py` (intero opzionale, default 50). La soglia 50
e' una proposta che bilancia copertura e peso del contesto; e' configurabile per
chi vuole piu' o meno ampiezza, non e' uno standard implicito.

La ricerca continua a raccogliere internamente tutti i match (il costo in
memoria su un diario locale e' trascurabile; cio' che pesa nel contesto e'
l'output serializzato). Alla fine, il tool restituisce:

- `risultati`: i primi `max_risultati` match (la lista troncata, e' questa che
  finisce nel contesto).
- `totale_risultati`: il numero TOTALE di match trovati (invariato come campo,
  conserva il conteggio pieno).
- `troncato`: booleano, `True` quando `totale_risultati > max_risultati`.
- `max_risultati`: il limite applicato, riportato per trasparenza.
- quando `troncato` e' `True`, un campo `nota` che suggerisce di restringere il
  range di date, usare `tipo` per filtrare le sorgenti, o alzare `max_risultati`.

Compatibilita': i test esistenti in `tests/test_cerca.py` asseriscono
`totale_risultati` con conteggi piccoli (0, 1, 3) e indicizzano `risultati[0]`.
Mantenendo `totale_risultati` come conteggio pieno e cappando solo `risultati`,
con default 50, questi test restano verdi senza modifiche.

Criterio di accettazione: con un set di 3 match e `max_risultati=2`, il tool
restituisce `len(risultati) == 2`, `totale_risultati == 3`, `troncato == True`,
e il campo `nota` presente; con `max_risultati` al default e pochi match,
`troncato == False` e nessuna `nota`.

### 2. Output compatto di `leggi_diario`

Modificare `leggi_diario` cosi' che i giorni mancanti non producano un oggetto
in `giorni`. La lista `giorni` contiene solo i giorni con file presente
(struttura invariata per quei giorni: data, file, titolo, entries, num_entries,
bloccanti). Le date mancanti vengono raccolte in una lista e riportate nel
riepilogo.

Forma del `riepilogo` dopo la modifica:

- `files_trovati` (invariato)
- `files_mancanti` (invariato, conteggio)
- `date_mancanti`: lista delle date (stringhe `YYYY-MM-DD`) dei giorni senza file

Il blocco `periodo` resta invariato (`da`, `a`, `giorni_totali`).

Cambio di contratto (dichiarato): per il caso a giorno singolo mancante, oggi
`leggi_diario` restituisce `giorni[0]["esiste"] == False`; dopo la modifica
`giorni` e' vuota e la data compare in `riepilogo.date_mancanti`. Questo rompe
due test in `tests/test_reader.py`:

- il test del giorno singolo mancante (intorno alle righe 26-27, che asserisce
  `result["giorni"][0]["esiste"] is False`);
- il test del range con un giorno mancante (intorno alle righe 41-43).

Entrambi vanno aggiornati al nuovo contratto: il giorno mancante non e' piu' in
`giorni` ma in `riepilogo.date_mancanti`; `files_trovati`/`files_mancanti`
restano come prima.

Criterio di accettazione: leggere un range di 2 giorni di cui uno esistente e
uno mancante restituisce `len(giorni) == 1` (solo quello esistente),
`riepilogo.files_mancanti == 1`, e `riepilogo.date_mancanti == ["<data
mancante>"]`. Leggere un singolo giorno mancante restituisce `giorni == []` e la
data in `date_mancanti`.

## Strategia di test

- Test-first per entrambi i blocchi: scrivere prima i test del nuovo
  comportamento, vederli fallire, poi implementare.
- `cerca`: nuovo test con `max_risultati` basso e piu' match del limite, piu' un
  test che il default non tronca su pochi match.
- `leggi_diario`: aggiornare i due test del contratto e aggiungere un test
  esplicito su `date_mancanti`.
- Aggiornare README (sezione `cerca`) per documentare `max_risultati`, `troncato`
  e `totale_risultati`, e la sezione `leggi_diario` per il nuovo `riepilogo`.
- Suite completa verde (zero test falliti), ruff pulito.

## Rischi e compromessi

- **Cambio di forma di `leggi_diario`.** E' un cambiamento di contratto
  d'output. Accettabile: il consumatore e' un singolo LLM locale, e la forma
  nuova (giorni reali + lista compatta di date mancanti) e' piu' pulita e piu'
  professionale degli stub per-giorno. I test che dipendono dalla vecchia forma
  vengono aggiornati nello stesso commit.
- **`cerca` raccoglie tutto in memoria prima di cappare.** Deliberato: il costo
  che conta e' l'output nel contesto, non la memoria Python su un diario locale.
  Raccogliere tutto permette di riportare `totale_risultati` reale e quindi di
  segnalare onestamente il troncamento.

## Fasi

Il piano (passo successivo, via writing-plans) sequenziera' B come: prima il
tetto di `cerca` (test-first), poi l'output compatto di `leggi_diario`
(test-first con aggiornamento dei due test esistenti), infine l'aggiornamento
del README per i due tool.
