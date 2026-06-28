# Sotto-progetto D3 — Ricerca per riferimento incrociato

Data: 2026-06-27
Stato: Design (in attesa di review)
Roadmap: A, B, C, D-fondazione, D1 (dossier), D2 (statistiche) fatte e pubblicate (v1.4.0). D3 aggiunge la ricerca incrociata per riferimento.

## Problema

`cronos_cerca` fa ricerca full-text e restituisce match grezzi senza sapere a
quale progetto appartengono. Per un lavoro ticket-heavy serve tracciare un
riferimento nel tempo e fra i progetti: "mostrami tutto cio' che tocca DVT-552",
"il filo della MR !258", "dove ho lavorato sul repo X". Cioe' una TIMELINE di un
riferimento, project-aware, con i progetti/sistemi che attraversa.

## Design

Nuovo tool `cronos_riferimento` (funzione `traccia_riferimento`), sola lettura.
Dato un riferimento (codice ticket, numero MR, nome repo, o qualunque stringa),
scandisce il diario nel periodo e restituisce ogni voce che lo menziona, marcata
col progetto canonico, piu' l'aggregazione dei progetti e sistemi coinvolti. E'
il fratello del dossier (D1), ma indicizzato su un riferimento invece che su un
progetto.

`traccia_riferimento(riferimento, data_inizio=None, data_fine=None, ultimi_giorni=180, max_voci=50)`:

1. Risolve il periodo come gli altri tool.
2. Per ogni giorno legge il file principale (`get_file_path`), lo segmenta con
   `split_entries_respecting_fences`. Per ogni chunk che inizia con `### `:
   se `riferimento` compare nel testo del chunk (intestazione + corpo,
   match case-insensitive), e' un hit. Raccoglie:
   `{data, progetto: canonical_projects(heading), titolo, snippet}`.
3. Aggrega: timeline cronologica (cappata a `max_voci`, piu' recenti), insieme
   dei progetti canonici coinvolti, insieme dei sistemi coinvolti (via
   `system_of`), num_voci, num_giorni, prima/ultima data.

### Output

```
{
  "riferimento": "DVT-552",
  "periodo": {"da": "...", "a": "..."},
  "num_voci": 7, "num_giorni": 4,
  "prima_data": "...", "ultima_data": "...",
  "progetti": ["SmarTicket"],          # canonici coinvolti, ordinati
  "sistemi": ["Teseo"],                 # sistemi coinvolti, ordinati
  "timeline": [{"data", "progetto", "titolo", "snippet"}],  # cappata
  "max_voci": 50, "troncato": false
}
```

Output compatto e cappato (stile fase B). Il match e' una sottostringa
case-insensitive del riferimento nel chunk: adatto a codici ticket ("DVT-552"),
MR ("!258"), nomi repo. Il chiamante passa un token specifico.

### Indipendenza e relazione con `cerca`

Come gli altri tool fa la propria segmentazione (`split_entries_respecting_fences`
+ `canonical_projects`), indipendente da `parse_entries`. Si distingue da
`cerca`: `cerca` e' full-text regex su raw/todo/chiusura senza progetto;
`cronos_riferimento` e' il filo project-aware e aggregato di UN riferimento nel
log raw. I due sono complementari.

## Non-obiettivi
- Nessuna integrazione live (lo stato reale del ticket su Jira e' D4): qui si
  cerca cio' che e' scritto nel diario.
- Nessuna ricerca sui file di chiusura/todo (solo il log raw, coerente con
  dossier e statistiche).
- Nessuna modifica a `parse_entries`.
- Nessun refactor dello scanner condiviso (debito noto: lista/dossier/statistiche/
  audit/riferimento ripetono il loop per-giorno; estrazione rimandata a uno slice
  dedicato che tocca tutti).

## Strategia di test
Test-first.
- Match di un ticket presente nel corpo di una voce -> hit con progetto canonico
  corretto; voce senza il riferimento -> esclusa.
- Match case-insensitive ("dvt-552" trova "DVT-552").
- Aggregazione: progetti e sistemi coinvolti corretti quando il riferimento
  compare in voci di progetti diversi.
- Cap `max_voci`/`troncato`; periodo senza hit -> risultato vuoto coerente.
- Suite verde, ruff pulito.
- **Documentazione (regole fisse):** README in ENTRAMBE le lingue (sezione
  `#### cronos_riferimento`, esempio NEUTRO), CLAUDE.md (tool count 18, scope
  `riferimento`, albero), e voce in `CHANGELOG.md` sotto `[Unreleased]`.

## Verifica sul campo
Dopo l'implementazione, eseguire `traccia_riferimento("DVT-...")` dal repo contro
il diario reale per confermare che il filo di un ticket reale venga ricostruito
con i progetti giusti.

## Rischi e compromessi
- **Match a sottostringa**: un token molto corto potrebbe over-matchare;
  l'utente passa token specifici (codici ticket/MR), accettabile.
- **Quinto uso del loop per-giorno**: debito DRY dichiarato, refactor dedicato a
  parte.

## Fasi
Il piano sequenziera': `tools/riferimento.py` con `traccia_riferimento`
(test-first), poi registrazione del tool `cronos_riferimento` in server.py,
infine doc (README EN+IT + CLAUDE.md + CHANGELOG [Unreleased]) + verifica sul
diario reale.
