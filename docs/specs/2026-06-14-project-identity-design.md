# Sotto-progetto D-fondazione — Identita' di progetto (modello a due livelli)

Data: 2026-06-14
Stato: Design (in attesa di review)
Roadmap: A, B, C fatte e pubblicate (v1.1.0). D si apre con questa fondazione, prerequisito di tutto il resto (dossier, statistiche, ricerca per progetto, report).

## Problema (evidenza dal diario reale)

Su 180 giorni, `cronos_lista_progetti` riporta **555 nomi distinti**, ma solo
**~35 sono progetti reali**; il ~93% e' rumore (titoli di sotto-sezione, liste
numerate, descrizioni di task finite nel nome, artefatti markdown, nomi composti
"A / B"). Cause radice: `extract_projects` spezza l'heading sul trattino " - " ma
l'utente usa l'em-dash " — ", e conta come progetti anche gli H3 di sotto-sezione;
inoltre lo stesso progetto compare in molte varianti ("SmarTicket" in 12 forme,
"Teseo" in 16). La chiave "progetto" e' frammentata alla radice, quindi ogni
feature di D costruita su di essa sarebbe inaffidabile.

## Tassonomia verificata (dai documenti del workspace)

Verificato in `/Users/mauriziomocci/Documents/workspace/sviluppo` —
`Teseo/CLAUDE.md` e `RAPSODIA/ECOSYSTEM.md` — non per intuizione:

- **Teseo NON e' un progetto fratello di SmarTicket: e' il sistema che lo
  contiene.** Teseo e' un ecosistema di microservizi Django per il TPL, composto
  da cinque componenti documentati: **Accounts, AppService, Infomobile, PayGW,
  SmarTicket** (`Teseo/CLAUDE.md`).
- Teseo e' una linea di prodotto fra le altre, non la cima di tutto. Linee
  separate, con namespace e Jira propri: **Rapsodia** (ecosistema a se':
  RapsodiaTrace, Beacon Service, Rapsodia Preferences Service, Rapsodia Keycloak),
  **IoPollicino** (Pollicino Hub + landing), **Goceano** (Jira GOA), **PiForte**
  (Jira PIF), **OpenTripPlanner** (motore di routing condiviso), e minori in
  `prod-misc` (Saras Bus Reservation, ctm-web-validators, Svoltiamo, TurmoTravel,
  3D Platform, Arrow2Go).
- Trasversali/non-prodotto: **MCP GreenShare** (== "MCP Teseo" == mcp-greenshare,
  il MCP di gestione, vive in `/MCP/Teseo` fuori da `sviluppo`), **MCP Cronos**
  (questo diario), **django-db-maintenance** (libreria), **Infrastruttura
  Kubernetes / cloud-kube** (ops trasversale), **Odoo** (esterno).

Conseguenza di design: serve un modello **a due livelli — sistema -> componente** —
con aggregazione che puo' salire al sistema o scendere al componente.

## Scalabilita' e multi-utente (requisito esplicito)

mcp-cronos e' un pacchetto pubblico (PyPI, MIT) e deve servire utenti con
progetti totalmente diversi da quelli GreenShare. Vincoli di design vincolanti:

- **Zero specificita' di dominio nel codice.** I nomi dei progetti (Teseo,
  Rapsodia, ...) NON compaiono mai nel pacchetto: vivono solo nel `cronos.toml`
  dell'utente. Il pacchetto esce con registro VUOTO.
- **Degrado elegante (funziona out-of-the-box).** Il registro e la whitelist
  sono OPT-IN. Con registro assente o vuoto — il caso di ogni nuovo utente —
  Cronos si comporta come oggi ma con il parsing migliorato (em-dash, composti,
  normalizzazione) e senza filtrare nulla: `lista_progetti` mostra i progetti
  cosi' come compaiono. La whitelist (contare solo i progetti dichiarati) e il
  modello a due livelli si attivano solo quando l'utente popola il registro,
  come raffinamento per chi ha uno storico rumoroso.
- **Onboarding generico.** Il tool `cronos_audit_progetti` aiuta qualunque utente
  a costruirsi il registro partendo dai nomi reali del proprio diario, senza
  alcuna assunzione sul dominio.
- **Schema di config generico.** `[cronos.projects]` con `sistema`/`alias` e'
  neutro: ogni utente modella i propri sistemi e componenti.

## Principio architetturale (non distruttivo)

I file markdown del diario NON vengono mai riscritti: restano la verita'.
L'identita' canonica si risolve a LETTURA/aggregazione, tramite un registro che
l'utente possiede in `cronos.toml`. Cambiare il registro cambia tutte le
aggregazioni senza toccare un file. Reversibile, sicuro, efficiente. Una
eventuale normalizzazione dei file su disco resta separata e opt-in, fuori da
questa spec.

## Design

### Registro a due livelli (config `[cronos.projects]`)

Ogni progetto canonico (componente) puo' dichiarare il sistema a cui appartiene
e gli alias-sinonimo. I sistemi sono i contenitori di primo livello; un progetto
senza `sistema` e' esso stesso un'entita' di primo livello (linea di prodotto o
trasversale).

```toml
# Componenti di Teseo: ogni voce dichiara il sistema padre e gli alias VERI
# (le differenze di sole maiuscole/spazi sono gestite dalla normalizzazione).
[cronos.projects.SmarTicket]
sistema = "Teseo"

[cronos.projects.Infomobile]
sistema = "Teseo"

[cronos.projects.PayGW]
sistema = "Teseo"
alias = ["PayGw"]

[cronos.projects.Accounts]
sistema = "Teseo"
alias = ["Microservizio Accounts"]

[cronos.projects.AppService]
sistema = "Teseo"
alias = ["AppManager"]

# Teseo come entita' di primo livello, per il lavoro taggato "Teseo" direttamente
# (cross-componente / piattaforma). Nessun `sistema`.
[cronos.projects.Teseo]
alias = ["Teseo Infra", "Infrastruttura Teseo", "Teseo Infrastruttura"]

# Altra linea di prodotto, con i suoi componenti.
[cronos.projects.RapsodiaTrace]
sistema = "Rapsodia"
alias = ["Rapsodia Tracking"]
# ... (registro completo precompilato durante l'implementazione, da rivedere)
```

Risoluzione a due meccanismi:

1. **Normalizzazione automatica** (in codice): minuscole, spazi collassati,
   suffissi "(BDI)"/"(Rapsodia)" rimossi, spazi attorno alla punteggiatura
   normalizzati. Cosi' "PayGw"/"PayGW", "BeaconService"/"Beacon Service",
   "Goceano"/"GOceano" combaciano col canonico senza elencarli. L'`alias` serve
   solo per sinonimi davvero diversi ("Rapsodia Tracking" -> RapsodiaTrace).

2. **Registro (whitelist), OPT-IN**: SOLO se il registro contiene almeno un
   progetto, contano solo i nomi che risolvono a un canonico noto e il resto e'
   "non classificato" (escluso dai conteggi ma mostrato dall'audit). Se il
   registro e' vuoto/assente — default per ogni nuovo utente — non si filtra
   nulla: vale il solo parsing migliorato (em-dash, composti, normalizzazione) e
   ogni nome parsato e' un progetto, come oggi. La whitelist e' quindi un
   raffinamento per storici rumorosi, non un requisito.

`CronosConfig` espone: `project_canonical: dict[str, str]` (alias-normalizzato ->
nome canonico), `project_system: dict[str, str]` (canonico -> sistema padre, se
presente), e la lista dei canonici e dei sistemi.

### Modulo di risoluzione (`utils/projects.py`, nuovo)

- `canonical_projects(heading: str) -> list[str]`: dato il testo-progetto di un
  H3, restituisce i progetti canonici (componenti). Scinde i composti su " / "
  (l'entry conta per ognuno), prende il token prima del separatore descrizione
  " - " o " — " (i trattini interni senza spazi, "django-db-maintenance", non si
  toccano), normalizza, risolve sul registro; non risolto -> scartato.
- `system_of(canonical: str) -> Optional[str]`: il sistema padre di un componente
  (es. "SmarTicket" -> "Teseo"), o None se e' gia' di primo livello.

Queste due funzioni sono la base su cui i prossimi slice di D costruiranno
dossier e statistiche, sia a livello di componente sia di sistema (roll-up).

### Hardening di `extract_projects` (markdown.py)

Reindirizzato attraverso `canonical_projects`: gestisce em-dash, composti, alias,
filtro del non-classificato. Resta fence-aware (gia' fatto in A).

### `cronos_lista_progetti` a due livelli

Aggrega per nome canonico, raggruppando i componenti sotto il loro sistema. Per
"Teseo" mostra il totale di sistema (somma dei componenti + entry dirette) e il
dettaglio per componente; per le linee senza componenti, la voce singola. I
composti contano per ogni progetto; il non classificato e' escluso; l'output e'
cappato (stile fase B). Si passa da 555 voci rumorose a ~35 progetti reali
organizzati per sistema.

### Nuovo tool `cronos_audit_progetti` (incl. bootstrap del registro)

Scansiona un periodo e restituisce, con output cappato: la mappatura nome grezzo
-> canonico -> sistema; la lista dei nomi NON classificati con conteggio e date
(candidati da aggiungere al registro o da ignorare); un riepilogo.

Per rendere SEMPLICE creare la lista dei progetti (requisito esplicito), emette
anche una **bozza pronta del blocco `[cronos.projects]`**: raggruppa i nomi
grezzi per forma normalizzata (i quasi-duplicati finiscono insieme), ordina per
frequenza, e propone per ogni cluster un nome canonico con le varianti come
alias. L'utente non scrive il registro da zero: lancia l'audit, ottiene i cluster
gia' fatti (la parte noiosa), aggiunge `sistema` dove vuole la gerarchia (la
parte di dominio che solo lui conosce), e salva nel suo `cronos.toml`. Il
clustering e' generico (vale per qualunque dominio); la gerarchia a due livelli
non si inventa automaticamente, resta una scelta dell'utente.

Il tool RESTITUISCE la bozza come testo, NON riscrive il `cronos.toml`: mutare in
automatico un file di config dell'utente sarebbe rischioso. L'assistente puo'
poi aiutare a salvarla. Funziona anche con registro vuoto, anzi e' lo strumento
di onboarding pensato proprio per quel caso.

### Seed del registro (precompilato, verificato)

Il seed e' DATO UTENTE, non un default del pacchetto: viene scritto nel
`cronos.toml` del diario dell'utente (il suo), non nel codice di mcp-cronos.
Materializzato durante l'implementazione, derivato dalla tassonomia verificata:

- **Teseo** (sistema) -> Accounts, AppService, Infomobile, PayGW, SmarTicket; piu'
  "Teseo" di primo livello per il lavoro cross-componente/piattaforma.
- **Rapsodia** (sistema) -> RapsodiaTrace, Beacon Service, Rapsodia Preferences
  Service, Rapsodia Keycloak.
- **IoPollicino** (sistema o entita') -> Pollicino Hub, Pollicino Landing Page
  (default: componenti di IoPollicino).
- Primo livello standalone: Goceano, PiForte, OpenTripPlanner, Saras Bus
  Reservation, ctm-web-validators, TurmoTravel, Svoltiamo, 3D Platform.
- Trasversali: MCP GreenShare (alias "MCP Teseo", "mcp-greenshare"), MCP Cronos,
  django-db-maintenance, Infrastruttura Kubernetes (alias "cloud-kube"), Odoo.

L'utente rivede questo seed: una correzione costa una riga. E' l'unico input che
richiede la sua conoscenza del dominio.

## Decisioni risolte (verificate o default modificabili)

- **Teseo = sistema** che contiene Accounts, AppService, Infomobile, PayGW,
  SmarTicket. (Verificato in `Teseo/CLAUDE.md` + conferma utente.)
- Rapsodia, IoPollicino, Goceano, PiForte, OTP: linee di prodotto separate, NON
  dentro Teseo. (Verificato: namespace e Jira distinti.)
- MCP GreenShare == MCP Teseo == mcp-greenshare: trasversale, distinto dal sistema
  Teseo e da MCP Cronos. (Verificato + conferma utente.)
- RapsodiaTrace e IoPollicino: distinti, stesso scopo, codebase separate; composto
  "RapsodiaTrace / IoPollicino" conta per entrambi. (Conferma utente.)
- Qualificatori-cliente ("ABT/CTM/ATPSS/Sardegna") riportati al sistema/componente
  base per default; tracciamento per-cliente come estensione futura.
- Beacon Service, Rapsodia Preferences Service, Rapsodia Keycloak: componenti di
  Rapsodia, distinti. "Rapsodia Tracking" -> RapsodiaTrace.
- Qualificatori d'ambiente ("/ Stage ...") e tooling one-off: non-progetto.

## Documentazione (requisito esplicito)

README (entrambe le lingue) e CLAUDE.md devono rendere CHIARO che:
- il registro dei progetti e' **facoltativo**; senza configurazione Cronos
  funziona out-of-the-box, e nessuna nozione di dominio e' cablata nel pacchetto;
- il modello a due livelli `sistema -> componente` e' generico e si modella nel
  proprio `cronos.toml`, con un esempio neutro (non Teseo);
- **come creare la lista dei progetti in modo semplice**: lanciare
  `cronos_audit_progetti`, ottenere la bozza di `[cronos.projects]` coi cluster
  gia' raggruppati, aggiungere la gerarchia dove serve, salvare. Un flusso di
  onboarding documentato passo-passo.

Una nuova sezione "Project registry (optional)" nel README copre questi tre
punti, con esempio generico.

## Non-obiettivi
- Nessuna specificita' di dominio (GreenShare/Teseo o altro) nel codice del
  pacchetto: tutto cio' che e' specifico vive nel `cronos.toml` dell'utente.
- Nessuna riscrittura dei file di diario (canonicalizzazione solo a lettura).
- Nessun dossier/statistica/report: slice successivi che poggiano su questa base.
- Nessun tracciamento per-cliente in questa fase.
- Nessun terzo livello sotto i componenti.

## Strategia di test
Test-first.
- `canonical_projects`: nome semplice -> [canonico]; "Progetto — descrizione" ->
  [canonico] (em-dash); composto "A / B" -> [A, B]; variante maiuscola/spazio ->
  [canonico] via normalizzazione; alias esplicito -> [canonico]; non classificato
  -> [].
- `system_of`: "SmarTicket" -> "Teseo"; "Goceano" -> None.
- `extract_projects`: heading reali misti -> solo canonici.
- config: `[cronos.projects]` letto, indici inversi (alias->canonico,
  canonico->sistema) costruiti, default vuoti.
- `cronos_lista_progetti`: aggregazione per canonico, raggruppamento per sistema,
  composti su entrambi, output cappato.
- `cronos_audit_progetti`: classificati vs non classificati, conteggi, cap.
- Suite verde, ruff pulito. README (`[cronos.projects]` + audit) e CLAUDE.md
  aggiornati.

## Rischi e compromessi
- **Whitelist vs blocklist.** Contare solo i progetti dichiarati e' piu' robusto;
  un progetto nuovo non compare finche' non e' nel registro, ma il tool di audit
  lo fa emergere. Compromesso accettato: memoria curata > memoria sporca.
- **Il seed puo' avere miei errori.** Mitigato: editabile in una riga, non
  distruttivo, e derivato da fonti verificate (non da intuizione).
- **Modello a due livelli.** Aggiunge un campo `sistema` e la logica di roll-up,
  ma e' necessario (lo dice la tassonomia reale) e abilita il dossier di sistema,
  che e' meta' del valore di "memoria di progetto".

## Appendice
La proposta grezza di mappa e' in `scratchpad/project-canonical-map-proposal.md`;
la tassonomia verificata viene dai doc del workspace citati sopra. Il seed
definitivo viene materializzato come `[cronos.projects]` in implementazione.

## Fasi
Il piano sequenziera': config registro a due livelli + indici inversi
(test-first), poi `utils/projects.py` (normalizzazione, `canonical_projects`,
`system_of`), poi hardening di `extract_projects`, poi `cronos_lista_progetti` a
due livelli, poi `cronos_audit_progetti`, infine seed verificato + doc.
