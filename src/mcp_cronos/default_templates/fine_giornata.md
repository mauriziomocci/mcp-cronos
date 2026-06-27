ISTRUZIONI PER LA CHIUSURA DI FINE GIORNATA:

Hai ricevuto le entry grezze del diario di oggi. Le entry restano nel file
`raw.md` della cartella giornaliera (e' il log progressivo della giornata,
con tutto il dettaglio tecnico). Il tuo compito qui e' produrre un file di
chiusura SNELLO e fruibile la mattina dopo, NON una ripetizione del raw.

Scrivi il risultato chiamando `cronos_scrivi_fine_giornata` con il contenuto
markdown completo. Il path di destinazione e' gestito dal tool stesso.

=== STRUTTURA DEL FILE DA SCRIVERE ===

```
# {titolo_standup}

## Riassunto

{riassunto_breve}

## Numeri salienti

{numeri_salienti}

## Decisioni prese

{decisioni}

## Punti aperti

{punti_aperti}

## Per riprendere il lavoro

{checkpoint_ripresa}

---

## Discorso per lo standup

{discorso_standup}

## Domande probabili e risposte pronte

{qa_standup}

---

## {section_blockers}

{bloccanti}
```

=== REGOLE GENERALI ===

- File snello (target: 50-100 righe). Il dettaglio sta in `raw.md`, qui
  serve solo cio' che e' utile la mattina dopo o allo standup.
- Tono diretto, da sviluppatore che spiega ad altri sviluppatori. Niente
  formalismi, niente disclaimer.
- Niente emoji.
- Niente attribuzione AI.
- Italiano tecnico con accenti corretti (e', a', perche', cioe' lasciali in
  ASCII solo dove serve compatibilita'; in prosa standup usa accenti veri).
  Per il "Discorso per lo standup" usa SEMPRE accenti unicode reali
  (e con accento, a con accento, perche con accento, cioe con accento, puo
   con accento, gia con accento, piu con accento) perche' sara' parlato.

=== SEZIONE: Riassunto ===

2-4 frasi che dicono in altissimo livello cosa ha occupato la giornata e
qual e' stato l'esito. Niente dettagli implementativi qui. Deve servire al
"me di domani mattina" per ricordare in 5 secondi di cosa si e' occupato.

Esempio:
"Giornata sul cleanup oauth2 dei microservizi ATPSS in produzione. Pulizia
massiva di 3.5M righe sui 4 servizi non bloccati, infrastruttura cleartokens
predisposta su tutti e 5 ma ancora suspended. worker-service resta bloccato sul
PVC saturo, decisione resize rimandata."

=== SEZIONE: Numeri salienti ===

Bullet list di cifre chiave del giorno. Solo numeri concreti che
testimoniano il volume di lavoro o il risultato. Massimo 5-7 bullet.

Esempio:
- 3.461.823 righe oauth2 cancellate su 4 microservizi
- 5 immagini Docker buildate e deployate
- 2 cron VACUUM riusciti, 3 falliti per env mancanti, tutti fixati
- 12 GiB usati su 15 del PVC db-lowq worker-service (saturazione 80%)

=== SEZIONE: Decisioni prese ===

Decisioni importanti prese oggi che incidono su lavoro futuro. Una riga
ciascuna, con il motivo se non ovvio. Massimo 5-6 voci.

Esempio:
- REFRESH_TOKEN_EXPIRE_SECONDS a 60 giorni in produzione (override manifest, default codice 30gg)
- Cron cleartokens lasciati suspended fino a dopo il weekend (validazione completata, ma niente run notturni durante festivi)
- Strategy A per worker-service: resize PVC + cleanup incrementale, NON cleartokens diretto

=== SEZIONE: Punti aperti ===

Cose lasciate a meta', task non ancora iniziati ma decisi, attese su altri.
Una riga ciascuna. Indica cosa serve per chiuderli.

Esempio:
- Resize PVC db-lowq worker-service 15->25 GiB (attesa autorizzazione utente)
- Risposta Domenico su REFRESH_TOKEN_EXPIRE_SECONDS (proposto 30/60 giorni)
- Unsuspend dei 4 cron cleartokens dopo il weekend
- VACUUM FULL automatico del 04/05: worker-service fallira' di nuovo se PVC non resized

=== SEZIONE: Per riprendere il lavoro ===

Il "checkpoint" preciso da consultare la mattina dopo per non perdere
contesto. Include: dove eravamo arrivati, cosa controllare per primo,
comandi utili pronti.

Stile pratico, copia-incollabile dove possibile.

Esempio:
"Domani mattina, prima di tutto verificare l'esito del VACUUM notturno:
```
kubectl get jobs -n prod-teseoapp-atpss -l k8s-role=cron --sort-by=.metadata.creationTimestamp
kubectl get pods -n prod-teseoapp-atpss --field-selector status.phase=Failed
```
Se worker-service e' di nuovo ENOSPC: aprire la conversazione PVC resize.
Altrimenti procedere con la sequenza unsuspend cron cleartokens."

=== SEZIONE: Discorso per lo standup ===

Paragrafo discorsivo in prima persona che leggero' allo standup. Deve
suonare come MIO discorso, non come testo generato. Frasi naturali, tono
colloquiale, transizioni vere ("poi", "intanto", "alla fine", "stamattina",
"nel pomeriggio"). Niente elenchi puntati, niente grassetto, niente
strutture rigide. Niente nomi di file, commit hash, MR, ticket Jira.

Regole:
- Prima persona, presente o passato prossimo
- Massima continuita' discorsiva: un flusso unico
- Alto livello: cosa, perche', con chi -- non come
- Se ci sono problemi/bloccanti, menzionarli alla fine in modo naturale
- Accenti unicode REALI (per esempio: perche con accento grave finale,
  pero con accento, gia con accento, ecc.) perche' verra' letto a voce
- Niente saluti, niente convenevoli, niente firme

Esempio (estratto da uno standup reale):
"Ieri ho dedicato tutta la giornata al cleanup oauth2 dei microservizi
ATPSS in produzione. La mattina sono partito guardando i log dei vacuum
notturni per capire perche' tre cron su cinque erano falliti, ho trovato
che mancavano delle env nei manifest e li ho sistemati. Poi ho fatto la
pulizia incrementale anno per anno sui quattro servizi che funzionavano,
e abbiamo recuperato circa tre milioni e mezzo di righe. Nel pomeriggio
ho preparato l'infrastruttura cleartokens su tutti e cinque, deployato le
nuove versioni, e validato il comportamento con due test on-demand. I cron
sono pero' ancora suspended, li attiveremo dopo il weekend. Resta aperto
il discorso worker-service: il volume e' saturo, il vacuum di stanotte
fallira' di nuovo se non facciamo il resize del PVC, sto aspettando
l'autorizzazione."

=== SEZIONE: Domande probabili e risposte pronte ===

Anticipa le domande che potrebbero farmi allo standup e prepara le
risposte. Format Q/A diretto, breve. Massimo 4-6 domande.

Le domande devono essere quelle realistiche di un team tech: dettagli
operativi che lo standup discorsivo non copre, validazioni di scelte,
attese, rischi. Le risposte vanno al punto, niente preamboli.

Esempio:
**D: Quanto spazio avete recuperato esattamente?**
R: Sui 4 servizi puliti circa 12 GB sui database, in dettaglio api-gateway
600MB, billing-service 1.2GB, web-frontend 8GB, auth-service 2.2GB. worker-service non
calcolabile finche' non sblocchiamo il PVC.

**D: Perche' i cron cleartokens non sono ancora attivi?**
R: Volevamo prima validare il comportamento e abbiamo fatto due test
on-demand. Validazione ok ma preferiamo non far partire i run notturni
durante il weekend, li attiviamo lunedi.

**D: Il fix dei tre cron vacuum vale anche per gli altri?**
R: Sono cinque cron identici per template, ho replicato le env block
mancanti su tutti e tre quelli che fallivano. Gli altri due (api-gateway,
web-frontend) avevano gia' le env corrette dal primo deploy.

**D: Cosa rischiamo se worker-service resta cosi' anche stanotte?**
R: Stesso ENOSPC del 30/04, il vacuum fallisce ma nessun impatto
applicativo. Il rischio reale e' il limite: a 90% di saturazione il DB
inizia a degradare, ora siamo all'80%. Settimana prossima resize obbligato.

=== PROCEDURA ===

1. Leggi attentamente le entry raw del giorno
2. Distilla i punti importanti separando "fatto" da "deciso" da "aperto"
3. Genera le sezioni mantenendo il file SNELLO -- se una sezione e' vuota
   metti "Nessuno" o "Niente" e vai avanti
4. Per il "Discorso per lo standup" rileggi a voce mentale per
   verificare che suoni naturale
5. Per le "Domande probabili" pensa alle domande sgradevoli, non solo
   quelle facili: cosa potrebbe contestare un tech lead?
6. Chiama `cronos_scrivi_fine_giornata` con il contenuto generato
7. Subito dopo la chiusura, prepara la cartella del prossimo giorno
   lavorativo con `cronos_prepara_domani`. Vedi sezione successiva.

=== PREPARAZIONE GIORNO SUCCESSIVO ===

Al termine della chiusura, chiama `cronos_prepara_domani` per impostare
il todo del prossimo giorno lavorativo (il tool calcola da solo: lun-gio
-> domani, ven/sab/dom -> lunedi successivo). Il tool crea anche il
raw.md scheletro per la giornata successiva (solo se non esiste gia').

Il `contenuto_todo` da passare e' un markdown autocontenuto. Il modello
da seguire:

```
# Da fare {giorno_settimana} {giorno} {mese} {anno}

Promemoria scritto la sera del {oggi} a fine giornata.

## 1. {prima cosa importante}

{descrizione concisa, comandi pronti se servono}

## 2. {seconda cosa}

{...}
```

Regole per il todo:
- Una voce per ogni "punto aperto" o "decisione da prendere" identificato
  nella chiusura.
- Includi comandi shell pronti quando l'azione e' operativa (kubectl,
  bash, ecc.) — la mattina dopo si copia-incolla.
- Includi link interni a memorie/diari/strategie pertinenti in fondo.
- Numerazione progressiva, con eventuale punto "0. PRIMA COSA" per cose
  che vanno fatte appena si apre il computer (es. commit pendenti dalla
  sera prima).
- Se non ci sono cose da fare, scrivi "## Nessun punto aperto" e basta:
  comunque crea il file per uniformita'.
