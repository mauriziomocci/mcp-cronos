# Sotto-progetto D2 — Statistiche per progetto e sistema

Data: 2026-06-27
Stato: Design (in attesa di review)
Roadmap: A, B, C, D-fondazione, D1 (dossier) fatte e pubblicate (v1.3.0). D2 affianca al dossier (la storia) i numeri (la distribuzione).

## Problema

Il dossier (D1) racconta la storia di un progetto, e `lista_progetti` da' un
conteggio grezzo per progetto. Manca una vista di sintesi: come si distribuisce
il lavoro fra progetti e sistemi in un periodo, e come si muove nel tempo.
Domande tipo "dove e' andato il mio mese?", "quanto Teseo vs Rapsodia?", "quali
progetti salgono o calano?". Con l'identita' canonica a due livelli ora c'e' la
base per rispondere.

## Design

Nuovo tool `cronos_statistiche` (funzione `statistiche`), sola lettura, sopra il
registro. Scansiona il periodo, conta le voci (ogni intestazione H3 che risolve
a un progetto canonico) e i giorni distinti per progetto, fa il roll-up per
sistema, e calcola la distribuzione temporale per mese.

Misura di sforzo = proxy su voci e giorni (NON time-tracking manuale, scelta
deliberata: tra incidenti e contesti multipli l'utente non compilerebbe le ore).

`statistiche(data_inizio=None, data_fine=None, ultimi_giorni=90, max_progetti=50)`:

1. Risolve il periodo come gli altri tool (range esplicito o ultimi N giorni).
2. Per ogni giorno legge il file principale (`get_file_path`), lo segmenta con
   `split_entries_respecting_fences`. Per ogni intestazione `### `, per ogni
   progetto canonico restituito da `canonical_projects`:
   - incrementa `voci[progetto]`;
   - aggiunge la data a `giorni[progetto]` (set, per contare i giorni distinti);
   - incrementa `per_mese[YYYY-MM]` (volume di attivita' nel tempo).
3. Roll-up per sistema via `system_of`: somma voci e giorni-distinti per sistema.
4. Totali: voci totali, giorni attivi distinti (qualunque progetto), numero
   progetti distinti, numero sistemi distinti.
5. Quota percentuale per sistema = voci sistema / voci totali.

### Output

```
{
  "periodo": {"da": "...", "a": "...", "giorni_analizzati": N},
  "totali": {"voci": ..., "giorni_attivi": ..., "progetti": ..., "sistemi": ...},
  "per_sistema": [{"sistema": "Teseo", "voci": ..., "giorni": ..., "quota_pct": 62.5}],  # ordinato per voci desc
  "per_progetto": [{"nome": ..., "sistema": ... , "voci": ..., "giorni": ...}],  # cappato a max_progetti, ordinato per voci desc
  "per_mese": {"2026-04": 30, "2026-05": 45, ...},  # trend temporale
  "max_progetti": 50, "troncato": false
}
```

Output compatto e cappato (stile fase B). `quota_pct` arrotondato a 1 decimale.
I progetti standalone (senza sistema) compaiono in `per_progetto` con
`sistema = null` e non contribuiscono ad alcuna voce di `per_sistema`.

### Indipendenza e coerenza

Come dossier e lista, fa la propria segmentazione (`split_entries_respecting_fences`
+ `canonical_projects`), quindi gestisce em-dash/composti/registro, senza
dipendere da `parse_entries`. Conta le VOCI (ogni intestazione), non i giorni:
quindi `voci` e' piu' granulare dell'`occorrenze` di `lista_progetti` (che conta
i giorni). I `giorni` per progetto sono riportati a parte.

## Non-obiettivi
- Nessun time-tracking manuale: sforzo = proxy voci/giorni.
- Nessuna integrazione esterna (Jira/GitLab/Docs): solo i dati del diario.
- Nessun grafico: numeri strutturati; la visualizzazione e' a carico del client.
- Nessuna modifica a `parse_entries`.

## Strategia di test
Test-first.
- `statistiche` con registro: voci e giorni per progetto corretti; roll-up per
  sistema con quota_pct; per_mese con trend su piu' mesi; totali coerenti
  (giorni_attivi distinti, progetti, sistemi); cap `max_progetti`/`troncato`.
- Senza registro (pass-through): conta i nomi grezzi parsati.
- Edge: periodo senza voci -> totali a zero, liste vuote, nessun crash.
- Suite verde, ruff pulito.
- **Documentazione (regola fissa):** README in ENTRAMBE le lingue (sezione
  `#### cronos_statistiche`, esempio NEUTRO non Teseo) e CLAUDE.md (tool count
  17, scope `stats`/`statistiche`, albero architettura) aggiornati nello stesso
  ciclo.

## Verifica sul campo
Dopo l'implementazione, eseguire `statistiche(ultimi_giorni=180)` dal repo contro
il diario reale dell'utente, per confermare la distribuzione Teseo/Rapsodia/altri
e il trend per mese.

## Rischi e compromessi
- **Sovrapposizione con lista_progetti**: `lista_progetti` resta la lista
  "leggera"; `statistiche` aggiunge sistema, quote e trend temporale. Accettabile:
  scopi diversi. Possibile futura estrazione di uno scanner condiviso (DRY), non
  in questo slice.
- **Proxy voci/giorni**: dichiarato; non misura ore reali.

## Fasi
Il piano sequenziera': `tools/statistiche.py` con `statistiche` (test-first),
poi registrazione del tool `cronos_statistiche` in server.py, infine doc
(README EN+IT + CLAUDE.md) + verifica sul diario reale.
