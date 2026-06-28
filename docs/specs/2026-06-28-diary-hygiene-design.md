# Sotto-progetto D6 — Igiene / doctor del diario

Data: 2026-06-28
Stato: Design (in attesa di approvazione)
Roadmap: A, B, C, D-fondazione, D1 (dossier), D2 (statistiche), D3 (riferimento) + refactor scanner condiviso fatti e pubblicati (v1.5.0). D4 (Jira/GitLab live) DE-SCOPED dal pacchetto core (decisione utente 2026-06-28: non utile a un utente generico). D6 aggiunge un controllo di igiene del diario.

## Problema

I tool di analisi (dossier D1, statistiche D2, riferimento D3) sono precisi solo quanto il dato sotto. Oggi nulla segnala quando il diario "scivola": una voce con intestazione che non risolve ad alcun progetto del registro resta INVISIBILE a dossier e statistiche; una fence di codice non chiusa rompe la segmentazione dell'intera giornata; un giorno lavorativo senza file e' un buco silenzioso; un giorno aperto ma mai chiuso (raw senza fine-giornata) resta a meta'. Serve un controllo di igiene, sola lettura, che fa emergere questi problemi col file e il contesto, prima che i deliverable (export, D5) ereditino il rumore.

E' la cura alla radice del rumore gia' osservato sui `riferimenti` del dossier: substrato pulito prima dei report.

## Design

Nuovo tool `cronos_igiene` (funzione `igiene_diario`), sola lettura. Scandisce il diario nel periodo e restituisce una lista di problemi per categoria, cappata, con data e dettaglio. Generico: nessuna dipendenza esterna, riusa lo scanner condiviso `iter_diary_days`, il calendario festivo-aware `is_working_day` e la risoluzione canonica `canonical_projects` gia' nel pacchetto.

`igiene_diario(data_inizio=None, data_fine=None, ultimi_giorni=180, max_problemi=100)`:

Risolve il periodo come gli altri tool. Esegue quattro controlli:

1. **progetto_non_registrato** — per ogni voce `### ...`, se il registro `[cronos.projects]` e' popolato e `canonical_projects(intestazione)` e' vuoto, la voce non appartiene ad alcun progetto noto: lavoro invisibile a dossier/statistiche. Si segnala con data + intestazione. SALTATO (con nota) se il registro e' vuoto: in pass-through tutto risolve, il check non avrebbe senso. E' il check di valore principale.

2. **fence_non_chiusa** — file il cui blocco di codice fenced (``` o ~~~) resta aperto a fine file. Rompe la segmentazione: tutte le voci successive si fondono. Nuovo helper `has_unclosed_fence(content)` in markdown.py che riusa la stessa regola di fence di `_split_entries_respecting_fences` (apertura >=3 caratteri, chiusura stesso carattere e lunghezza, niente info-string). Si segnala col file.

3. **giorno_lavorativo_mancante** — giorno lavorativo nel periodo (festivo-aware via `is_working_day`, salta weekend e festivi nazionali del paese configurato) senza alcun file diario. Rilevatore di buchi. Cappato per non esplodere su periodi lunghi con pochi giorni scritti.

4. **chiusura_mancante** — giorno del layout nuovo con `raw.md` presente ma senza `fine-giornata.md`: giornata aperta e mai chiusa. I giorni legacy a file singolo sono ESCLUSI (la chiusura e' inline, non esiste un file separato — `has_legacy_file`).

### Output

Ogni problema e' AZIONABILE: oltre a `tipo`/`data`/`dettaglio` porta una `gravita` e un `suggerimento` concreto su come risolverlo. In cima un `riepilogo` in linguaggio umano riassume tutto in una frase, cosi' l'assistente (o l'utente) capisce subito cosa conta senza scorrere la lista.

```
{
  "periodo": {"da": "...", "a": "...", "giorni_analizzati": 180},
  "registro_attivo": true,
  "riepilogo": "6 problemi: 0 critici, 3 avvisi, 3 info — 3 voci fuori registro, 2 giorni feriali senza diario, 1 giornata non chiusa.",
  "problemi": [
    {"tipo": "progetto_non_registrato", "gravita": "avviso", "data": "2026-06-27",
     "dettaglio": "Supporto / Ticket Odoo - HT17969 ...",
     "suggerimento": "Intestazione non mappata ad alcun progetto del registro: questa voce non compare in dossier/statistiche. Aggiungi un alias in [cronos.projects], oppure rilancia cronos_audit_progetti per rigenerare la bozza."},
    {"tipo": "fence_non_chiusa", "gravita": "critico", "data": "2026-05-12",
     "dettaglio": "blocco di codice aperto a fine file",
     "suggerimento": "Chiudi il blocco con una riga di soli backtick (```): finche' resta aperto, tutte le voci successive di quel giorno si fondono e spariscono dalle analitiche."},
    {"tipo": "giorno_lavorativo_mancante", "gravita": "info", "data": "2026-06-10",
     "dettaglio": "giorno lavorativo senza diario",
     "suggerimento": "Se era una giornata di ferie/malattia ignora; altrimenti il giorno non e' tracciato."},
    {"tipo": "chiusura_mancante", "gravita": "info", "data": "2026-06-20",
     "dettaglio": "raw.md presente, fine-giornata.md assente",
     "suggerimento": "Giornata aperta e mai chiusa: usa cronos_scrivi_fine_giornata per chiuderla."}
  ],
  "conteggi": {"progetto_non_registrato": 3, "fence_non_chiusa": 0, "giorno_lavorativo_mancante": 2, "chiusura_mancante": 1},
  "conteggi_gravita": {"critico": 0, "avviso": 3, "info": 3},
  "totale_problemi": 6,
  "max_problemi": 100, "troncato": false,
  "note": []        # es. ["registro vuoto: check progetto_non_registrato saltato"]
}
```

Mappa gravita->tipo: `fence_non_chiusa` = **critico** (corrompe i dati di quel giorno), `progetto_non_registrato` = **avviso** (lavoro intatto ma invisibile alle analitiche), `giorno_lavorativo_mancante`/`chiusura_mancante` = **info**. Il `suggerimento` e' una stringa di rimedio per tipo (generica, nessun dominio). Output compatto e cappato (stile fase B): i problemi sono ordinati per gravita' poi per data; il cap si applica alla lista, mentre `conteggi`/`conteggi_gravita` restano TOTALI (cosi' "troncato" non nasconde quanti problemi reali ci sono).

### Aiuto all'utente e usabilita'

Il tool e' un advisor, non solo un rilevatore: per ogni problema dice cosa fare. Il check #1 chiude il cerchio con `cronos_audit_progetti` — audit COSTRUISCE il registro (bootstrap), igiene lo MANTIENE e indica la riga da aggiungere quando una voce sfugge.

A corredo, il README guadagna un "Per iniziare" di quattro passi che rende SEMPLICE creare la lista progetti (requisito esplicito, valido per qualunque utente):
1. Scrivi le voci della giornata come al solito (`### Progetto - Descrizione`).
2. Lancia `cronos_audit_progetti`: clusterizza i nomi grezzi e produce una bozza `[cronos.projects]` pronta.
3. Incolla la bozza in `cronos.toml` (e ritocca alias/gerarchia a piacere).
4. Lancia `cronos_igiene`: verifica che tutto risolva e segnala cosa resta fuori.

Questo trasforma audit+igiene in un ciclo costruisci->mantieni chiaro e documentato.

### Indipendenza e relazione con `audit`

`cronos_audit_progetti` (D-fondazione) guarda i nomi grezzi per COSTRUIRE il registro (bootstrap). `cronos_igiene` presuppone il registro gia' costruito e segnala dove il diario se ne discosta o e' malformato. Complementari: audit per partire, igiene per mantenere.

## Debito incluso: parse_entries em-dash

`parse_entries` (markdown.py) splitta l'intestazione `### Progetto - Descrizione` solo su `" - "` (trattino-spazi), non sull'em-dash `" — "`. Le intestazioni che usano l'em-dash finiscono con progetto = tutta l'intestazione. `canonical_projects`/`project_tokens` gia' gestiscono l'em-dash; qui si allinea `parse_entries` per coerenza (split anche su `" — "`). Fix piccolo, debito noto chiuso.

## Non-obiettivi
- Nessuna correzione automatica: sola lettura, segnala e basta (niente riscrittura del markdown).
- Nessun nuovo concetto di validita': si usano le regole gia' codificate (sezioni config, regola fence, registro, calendario).
- Nessun flag su `## ` dentro il corpo di una voce: sono prosa legittima (sotto-titoli), NON header di sezione. Solo `## {section_entries}`/`## {section_blockers}` sono strutturali (come gia' fa il parser).
- Niente "vocabolario dei riferimenti" (Repo vs Repository): utile ma e' materia da report (D5), non da doctor.

## Strategia di test
Test-first.
- progetto_non_registrato: con registro popolato, voce con intestazione fuori registro -> segnalata; voce con progetto noto -> no. Con registro vuoto -> check saltato + nota.
- fence_non_chiusa: file con fence aperta -> segnalato; file ben formato -> no. `has_unclosed_fence` testato in isolamento (fence chiusa, aperta, annidata a 4 backtick, nessuna fence).
- giorno_lavorativo_mancante: buco in giorno feriale -> segnalato; weekend/festivo senza file -> NO.
- chiusura_mancante: layout nuovo con raw senza fine-giornata -> segnalato; con fine-giornata -> no; giorno legacy -> escluso.
- Cap `max_problemi`/`troncato`; conteggi restano totali oltre il cap; periodo pulito -> liste vuote coerenti.
- parse_entries: intestazione con em-dash -> progetto e descrizione splittati correttamente.
- Suite verde, ruff pulito (check + format).
- **Documentazione (regole fisse):** README in ENTRAMBE le lingue (sezione `#### cronos_igiene`, esempio NEUTRO), CLAUDE.md (tool count 19, scope `igiene`, albero), e voce in `CHANGELOG.md` sotto `[Unreleased]`.

## Verifica sul campo
Dopo l'implementazione, eseguire `igiene_diario()` dal repo contro il diario reale: confermare che le voci tipo "Supporto / Ticket Odoo" emergano come progetto_non_registrato (lavoro reale invisibile alle analitiche), e che i conteggi siano plausibili.

## Rischi e compromessi
- **Rumore del doctor**: ironia da evitare. Per questo solo 4 check ad alto segnale, cap, e il check #1 saltato quando il registro e' vuoto. Niente flag su prosa `## `.
- **giorno_lavorativo_mancante su periodi lunghi**: ferie/malattia generano molti "buchi" leciti. Festivo-aware riduce; il cap protegge; resta informativo, non un errore.

## Fasi
Il piano sequenziera': (1) `has_unclosed_fence` in markdown.py (test-first); (2) fix em-dash in `parse_entries` (test-first); (3) `tools/igiene.py` con `igiene_diario` (test-first, 4 check); (4) registrazione tool `cronos_igiene` in server.py; (5) doc (README EN+IT + CLAUDE.md tool-count 19 + CHANGELOG [Unreleased]) + verifica sul diario reale.
