# Sotto-progetto D1 — Dossier per progetto

Data: 2026-06-27
Stato: Design (in attesa di review)
Roadmap: A, B, C, D-fondazione (identita' progetto) fatte e pubblicate (v1.2.0). D1 e' il primo slice di valore sopra la chiave canonica.

## Problema

Oggi per ricostruire "cosa ho fatto sul progetto X negli ultimi mesi, e cosa e'
rimasto aperto" l'utente deve cercare a mano nel diario. `cronos_cerca` trova
occorrenze testuali, `lista_progetti` da' solo conteggi. Manca la **storia
completa di un progetto**: la sequenza cronologica del lavoro, i riferimenti
(repo, branch, ticket, MR) accumulati, e i bloccanti incontrati. Con l'identita'
canonica a due livelli ora disponibile (D-fondazione), questo diventa possibile
in una sola domanda, sia per un singolo progetto sia per un intero sistema
(roll-up dei componenti).

## Design

Nuovo tool `cronos_progetto` (funzione `dossier_progetto`) che, dato un progetto
o un sistema e un periodo, assembla il dossier dal diario, a sola lettura.

### Risoluzione del target (componente o sistema)

Aggiungere a `utils/projects.py`:
- `members_of(target: str) -> set[str]`: i nomi canonici da includere nel
  dossier. Se `target` e' un SISTEMA (compare come valore in
  `config.project_system`), restituisce tutti i componenti con
  `sistema == target` PIU' lo stesso `target` (per il lavoro taggato sul sistema
  direttamente, es. "Teseo" piattaforma/infra). Altrimenti restituisce
  `{target_canonico}`. Il `target` in ingresso viene prima normalizzato e
  risolto al canonico via il registro (cosi' "mcp teseo" trova "MCP GreenShare");
  se non risolve a nessun canonico noto e non e' un sistema, si usa il target
  cosi' com'e' (modalita' pass-through / nessun registro).

### Assemblaggio del dossier

`dossier_progetto(progetto, data_inizio=None, data_fine=None, ultimi_giorni=180, max_voci=50)`:

1. Risolve il periodo (come `cerca`/`lista_progetti`): range esplicito, oppure
   ultimi N giorni.
2. Calcola `target_set = members_of(progetto)`.
3. Per ogni giorno del periodo, legge il file principale (`get_file_path`, cioe'
   raw o legacy), lo segmenta con `split_entries_respecting_fences`. Per ogni
   chunk che inizia con `### `, calcola `canonical_projects(heading)`; se
   l'intersezione con `target_set` non e' vuota, raccoglie la voce:
   `{data, progetto: <canonico/i che matchano>, titolo: <heading ripulito>,
   snippet: <primi ~200 char del corpo>}`. Estrae anche i riferimenti del corpo
   con `extract_references` e li accumula.
4. Raccoglie i bloccanti: per i giorni in cui il progetto compare, se la sezione
   bloccanti del file (via `parse_diary_file().bloccanti`) e' diversa dal
   default "Nessuno"/"None", la aggiunge come `{data, testo}`. (I bloccanti nel
   diario sono per-giornata, non per-progetto: vengono quindi etichettati per
   data e presentati come "bloccanti nei giorni in cui il progetto e' stato
   toccato", non attribuiti al progetto in modo finto.)
5. Ordina la timeline cronologicamente. Applica il cap `max_voci` alla timeline
   (con flag `troncato`), mantenendo le voci piu' recenti.

### Output

```
{
  "progetto": "Teseo",
  "e_sistema": true,
  "membri": ["Teseo", "SmarTicket", "Infomobile", "PayGW", "Accounts", "AppService"],
  "periodo": {"da": "...", "a": "..."},
  "num_voci": 42, "num_giorni": 18,
  "prima_data": "...", "ultima_data": "...",
  "per_progetto": {"SmarTicket": 30, "Infomobile": 8, ...},   # conteggio per componente (se sistema)
  "timeline": [{"data", "progetto", "titolo", "snippet"}],     # cappata a max_voci, recenti
  "riferimenti": {"repository": [...], "branch": [...], "jira": [...], "gitlab_mr": [...]},  # unici
  "bloccanti": [{"data", "testo"}],
  "max_voci": 50, "troncato": false
}
```

Output compatto e cappato (stile fase B): snippet brevi, riferimenti
deduplicati, timeline limitata. Un dossier su mesi non deve esplodere nel
contesto.

### Indipendenza da `parse_entries`

Il dossier fa la propria segmentazione (`split_entries_respecting_fences`) e
risolve il progetto con `canonical_projects` sull'intestazione, quindi gestisce
em-dash, composti e registro correttamente, SENZA dipendere dallo split " - "
di `parse_entries`. (Il debito di `parse_entries` resta separato e fuori scope.)

## Non-obiettivi
- Nessuna modifica a `parse_entries` (debito separato).
- Nessuna estrazione semantica avanzata dei "punti aperti": in v1 i bloccanti
  per-giornata sono il segnale di pendenza; un tracking esplicito dei to-do
  aperti per progetto e' una possibile iterazione futura.
- Nessuna integrazione live coi ticket (D4): i riferimenti sono quelli annotati
  nel diario, non lo stato reale Jira/GitLab.
- Nessuna lettura dei file di chiusura (`fine-giornata.md`): la timeline viene
  dal log raw, coerente con `cerca`/`lista_progetti`.

## Strategia di test
Test-first.
- `members_of`: sistema "Teseo" -> componenti + "Teseo"; componente "SmarTicket"
  -> {"SmarTicket"}; standalone "Goceano" -> {"Goceano"}; alias "MCP Teseo" ->
  {"MCP GreenShare"} (risoluzione al canonico).
- `dossier_progetto` con registro: dossier di un sistema raccoglie le voci di
  tutti i componenti + dirette; di un componente solo le sue; timeline ordinata;
  riferimenti deduplicati; bloccanti etichettati per data; cap `max_voci`/`troncato`.
- Senza registro (pass-through): dossier di un nome grezzo raccoglie le sue voci.
- Edge: progetto senza voci nel periodo -> dossier vuoto coerente (num_voci 0).
- Suite verde, ruff pulito. README (sezione tool + esempio neutro) e CLAUDE.md
  (tool count 16, scope `dossier`) aggiornati.

## Verifica sul campo
Dopo l'implementazione, eseguire `dossier_progetto("Teseo", ultimi_giorni=180)` e
`dossier_progetto("SmarTicket", ...)` dal repo (codice 1.2.x) contro il diario
reale dell'utente con il suo `cronos.toml`, per confermare che il roll-up di
sistema e il singolo componente producono una storia sensata.

## Rischi e compromessi
- **Bloccanti per-giornata, non per-progetto**: dichiarato; etichettati per data,
  non attribuiti in modo fuorviante.
- **Doppia segmentazione** (il dossier ri-segmenta invece di riusare
  `parse_entries`): scelta deliberata per correttezza canonica e per non toccare
  `parse_entries`; costo minimo su scala personale.

## Fasi
Il piano sequenziera': `members_of` in projects.py (test-first), poi
`tools/dossier.py` con `dossier_progetto` (test-first), poi registrazione del
tool `cronos_progetto` in server.py, infine doc + verifica sul diario reale.
