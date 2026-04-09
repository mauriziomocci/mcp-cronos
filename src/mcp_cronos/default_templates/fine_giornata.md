ISTRUZIONI PER LA CHIUSURA DI FINE GIORNATA:

Hai ricevuto le entry grezze del diario di oggi. Devi produrre un file markdown
completo con CINQUE sezioni, poi scriverlo al path indicato in `file`.

=== STRUTTURA DEL FILE DA SCRIVERE ===

```
# {titolo_standup}

## {section_day_summary}

{riassunto_giornata}

## {section_tech_summary}

{riassunto_tecnico}

---

## {section_standup_message}

{messaggio_standup}

---

## {section_entries}

{entries_riscritte}

---

## {section_blockers}

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
