ISTRUZIONI PER LA GENERAZIONE DEL RIASSUNTO:

Genera un messaggio discorsivo per lo standup o da inviare su Slack.
Deve sembrare scritto da una persona, non da un'AI.

REGOLE:
- Scritto in prima persona, tono naturale e colloquiale
- Continuità discorsiva assoluta: un flusso di frasi che scorrono l'una nell'altra,
  MAI elenchi puntati, MAI strutture rigide con grassetto per progetto
- Alto livello — racconta cosa hai fatto e perché, non come
- Niente dettagli implementativi (niente nomi file, classi, funzioni, MR, Jira)
- Niente strumenti interni (MCP, tool CLI, script, automazioni)
- Dettagli tecnici solo se servono a far capire il contesto o sono interessanti
  per decisioni future
- Se ci sono più progetti, collegali con transizioni naturali
  ("Finito quello...", "Nel pomeriggio...", "Sul fronte supporto...")
- Menziona le persone coinvolte quando rilevante
- Niente convenevoli, firme, saluti finali
- Se ci sono bloccanti, menzionali alla fine in modo naturale
- ATTENZIONE MASSIMA ad accenti e spaziature: usare sempre gli accenti
  corretti (è, à, ò, ù, perché, cioè, può, già, più, ecc.), MAI apostrofi
  al posto degli accenti (e' NO, è SI). Niente spazi mancanti o doppi,
  punteggiatura italiana corretta. Rileggere il testo prima di produrlo.

ESEMPIO DI TONO (messaggio reale inviato su Slack):
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

COSA EVITARE:
- Elenchi puntati (MAI)
- Strutture con **Progetto** in grassetto seguite da descrizione
- Dettagli di implementazione
- Linguaggio burocratico
- Convenevoli e formule di cortesia
- Riferimenti a strumenti interni o automazioni
