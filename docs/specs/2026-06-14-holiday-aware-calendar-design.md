# Sotto-progetto C1 — Calendario consapevole dei festivi

Data: 2026-06-14
Stato: Design (in attesa di review)
Roadmap: A (fatta) -> B (fatta) -> C (workflow giornaliero) -> D (capacita' professionali).
C e' decomposta in: **C1 festivi (questo)**, C2 auto-detect git, C3 default intelligenti, C4 chiusura serale unica.

## Problema

Cronos calcola il "prossimo giorno lavorativo" e l'"ultimo giorno lavorativo"
saltando solo sabato e domenica, **non i giorni festivi**. Verificato nel
sorgente: `get_next_working_day` in `src/mcp_cronos/utils/dates.py` usa delta
fissi (venerdi -> +3, sabato -> +2, domenica -> +1, altrimenti +1) e non
conosce le feste; `_ultimo_giorno_lavorativo` in `src/mcp_cronos/tools/standup.py`
decrementa finche' il giorno e' sabato/domenica, sempre ignorando le feste.

Conseguenza concreta: chiudendo il diario il 24 dicembre, `cronos_prepara_domani`
(che usa `get_next_working_day`) prepara il 25 dicembre, che e' Natale. Lo stesso
vale per qualunque vigilia di festa infrasettimanale e, specularmente, per il
calcolo dell'ultimo giorno lavorativo usato dallo standup.

## Obiettivi

- Il calcolo del prossimo e dell'ultimo giorno lavorativo salta i giorni festivi
  oltre ai weekend.
- I festivi nazionali sono riconosciuti tramite una libreria di calendari
  mantenuta e configurabile per paese (default Italia), cosi' Pasquetta (variabile
  ogni anno) e le altre feste sono gestite senza liste hardcoded.
- L'utente puo' aggiungere date proprie (ponti, chiusure aziendali, ferie) nella
  configurazione, che vengono trattate come festivi a tutti gli effetti.

## Non-obiettivi

- Nessuna festa locale/patronale per default (solo calendario nazionale); chi la
  vuole puo' aggiungerla come data extra in configurazione.
- Nessuna modifica al flusso di fine giornata oltre al fatto che, usando
  `get_next_working_day`, eredita automaticamente la consapevolezza dei festivi.
- C2/C3/C4 restano fuori da questo spec (cicli separati).

## Design

### Dipendenza

Aggiungere la libreria `holidays` (PyPI, mantenuta, pure-Python, configurabile
per paese e con calcolo automatico delle feste mobili come la Pasqua) alle
`dependencies` di `pyproject.toml`, installandola con `uv add holidays` cosi' che
anche `uv.lock` venga aggiornato. E' la scelta piu' professionale ed estensibile
ad altri paesi, coerente con l'impianto i18n gia' presente (it/en).

### Configurazione

Nuova sezione opzionale in `cronos.toml`:

```toml
[cronos.calendar]
# Codice paese ISO per il calendario festivi nazionale (default "IT").
country = "IT"
# Date extra trattate come festive (ponti, chiusure, ferie), YYYY-MM-DD.
extra_holidays = ["2026-12-07", "2026-08-14"]
```

Esporre su `CronosConfig` due campi: `calendar_country: str` (default "IT") e
`calendar_extra_holidays: list[str]` (default lista vuota), risolti in
`load_config()` dalla sezione `[cronos.calendar]` con la stessa logica
override-utente > default gia' usata per le altre impostazioni.

### Modulo festivi

Nuovo modulo `src/mcp_cronos/utils/workdays.py` (nome scelto per non confondersi
con lo stdlib `calendar`, gia' importato in `lista_mese.py`, ne' con la libreria
`holidays` importata al suo interno) con:

- `is_holiday(d: date) -> bool`: True se `d` e' una festa nazionale del paese
  configurato OPPURE e' fra le `extra_holidays`. Usa
  `holidays.country_holidays(country)` (che espande gli anni su richiesta) per il
  calendario nazionale. Le date extra vengono lette dalla config come stringhe e
  confrontate. Se il codice paese non e' valido o la libreria solleva, ricade in
  modo robusto sul "solo calendario extra" senza sollevare (un calendario
  nazionale assente non deve mai rompere il calcolo del giorno lavorativo).
- `is_working_day(d: date) -> bool`: True se `d.weekday() < 5` (lun-ven) e
  `not is_holiday(d)`.

### Calcolo giorni lavorativi (in `dates.py`)

Riscrivere `get_next_working_day(from_date)` come ciclo: partendo da
`from_date + 1 giorno`, avanza di un giorno alla volta finche' trova un giorno
lavorativo (`is_working_day`). Questo gestisce in modo naturale weekend, feste
singole e feste consecutive (es. 25-26 dicembre) e i ponti configurati, senza
delta fissi.

Aggiungere `get_previous_working_day(from_date)` come ciclo speculare: partendo da
`from_date - 1 giorno`, indietreggia finche' trova un giorno lavorativo.

Per evitare un ciclo infinito teorico (configurazione patologica che marca tutti
i giorni come festivi), entrambi i cicli hanno un limite di sicurezza di, ad
esempio, 366 iterazioni; raggiunto il limite restituiscono il candidato corrente
e l'anomalia e' comunque improbabile in uso reale.

`dates.py` importa `is_working_day` da `utils/workdays.py`. Attenzione all'ordine
degli import per evitare cicli: `workdays.py` dipende da `config.load_config`
(per country/extra) ma NON da `dates.py`, quindi non c'e' import circolare.

### Refactor standup

In `src/mcp_cronos/tools/standup.py`, sostituire il corpo di
`_ultimo_giorno_lavorativo` con una chiamata a `get_previous_working_day` cosi'
che lo standup salti anche le feste quando cerca l'ultimo giorno lavorativo.
Mantenere la firma della funzione per non toccare i chiamanti.

## Compatibilita' con i test esistenti

I test di `get_next_working_day` in `tests/test_dates.py` usano date di maggio
2026 (dal 04 all'11), in cui non cade alcuna festa nazionale italiana: con la
logica festivo-aware questi test restano verdi senza modifiche (il ciclo produce
gli stessi risultati dei vecchi delta quando non ci sono feste). Va comunque
verificato eseguendo la suite.

## Strategia di test

Test-first. Nuovi test:

- `utils/workdays.py`: `is_holiday` True per Natale 2026-12-25 e Pasquetta
  2026-04-06 (festa mobile), False per un feriale qualunque non festivo;
  `is_working_day` coerente.
- `get_next_working_day` festivo-aware: da giovedi 2026-12-24 -> lunedi
  2026-12-28 (salta Natale 25, Santo Stefano 26, weekend); da venerdi 2026-04-03
  -> martedi 2026-04-07 (salta weekend e Pasquetta lunedi 06).
- `extra_holidays` da config: con `extra_holidays=["2026-12-07"]`, da venerdi
  2026-12-04 -> mercoledi 2026-12-09 (salta lunedi 07 ponte configurato e martedi
  08 Immacolata festa nazionale).
- `get_previous_working_day`: da lunedi 2026-12-28 -> giovedi 2026-12-24 (salta
  weekend, Santo Stefano, Natale).
- I test esistenti di maggio devono restare verdi.

Config: `calendar_country` default "IT", `extra_holidays` letta correttamente.

Documentazione: aggiornare README (sezione `cronos.toml`) e CLAUDE.md per la
nuova sezione `[cronos.calendar]` e il comportamento festivo-aware. Suite verde,
ruff pulito.

## Rischi e compromessi

- **Nuova dipendenza (`holidays`).** Accettabile e deliberata: e' pure-Python,
  mantenuta, e copre con precisione le feste mobili (Pasquetta) che a mano
  sarebbero soggette a errori. Configurabile per paese, coerente con la north
  star "professionale ed estensibile".
- **Codice paese non valido.** Gestito con fallback robusto al solo calendario
  extra, mai un'eccezione che blocchi il calcolo del giorno lavorativo.
- **Ciclo di ricerca giorno lavorativo.** Limite di sicurezza a 366 iterazioni
  contro configurazioni patologiche.

## Fasi

Il piano (via writing-plans) sequenziera' C1 come: dipendenza + modulo
`workdays.py` (test-first), poi config plumbing, poi riscrittura dei calcoli
giorno-lavorativo in `dates.py` e refactor standup (test-first), infine
aggiornamento di README e CLAUDE.md.
