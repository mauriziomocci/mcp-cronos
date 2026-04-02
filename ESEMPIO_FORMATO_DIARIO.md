# Formato Diario - Guida ed Esempi

## Struttura Consigliata

Usa questa gerarchia per strutturare le entry del diario:

- `#` (H1): Titolo del file "Per lo Stand-up {Data}"
- `##` (H2): Sezioni principali "Cosa ho fatto ieri" e "Bloccanti"
- `###` (H3): Entry principali "{Progetto} - {Descrizione}"
- `####` (H4): Sottosezioni/dettagli della entry (opzionale ma consigliato)

---

## Esempio 1: Code Review

```markdown
### SmarTicket - Code Review MR #211 - Vouchers table improvements

Effettuata code review della MR #211 che implementa miglioramenti alla sezione voucher della vendor dashboard: separazione in due tabelle (voucher con prodotti e voucher con acquisti), aggiunta filtri e bottone reinvio email.

#### Problemi Identificati

1. **CSRF su ResendVoucherEmailView**: l'invio email usa GET invece di POST con CSRF token
2. **ListView contract violation**: get_queryset() restituisce una lista invece di un QuerySet

Pubblicato commento di review su GitLab MR e su Jira DVT-359.

**Riferimenti:**
- Repository: smarticket_project
- Branch: `improvements/display-vouchers-table-with-purchases`
- Jira: [DVT-359](https://mimmo7.atlassian.net/browse/DVT-359)
- Gitlab Mr: [MR !211](https://gitlab.greenshare.it/arrow_to_go/smarticket_project/-/merge_requests/211)
```

**Risultato messaggio Slack:**
> **SmarTicket** - Code review MR #211 di Anton (miglioramenti tabella voucher): richieste modifiche per vulnerabilità CSRF sul reinvio email (usa GET invece di POST) e perché usa ListView per gestire due tabelle separate quando serve TemplateView.

---

## Esempio 2: Bug Fix con Deploy

```markdown
### SmarTicket - Fix filtro date default in vendor_dashboard/purchases/v4

Risolto bug nel filtro date della pagina purchases/v4 del vendor dashboard. Il filtro non mostrava le vendite di oggi quando si accedeva alla pagina senza impostare un range di date.

#### Causa del Bug

- Variabile `end_dt_max_seconds` creata prima che `end_dt` fosse impostata correttamente
- Uso di `timezone.now()` (UTC) invece del timezone locale (Europe/Rome)
- Il filtro cercava record nell'intervallo UTC invece che Europe/Rome

#### Fix Applicato

- Rimossa variabile `end_dt_max_seconds` (dead code)
- Aggiunto `timezone.localtime()` per convertire nel timezone locale
- Impostato `microsecond=999999` per coprire l'intera giornata

#### Deploy in Produzione (v3.125.4)

- ATPSS
- BDI
- Nuoro
- Sardegna
- TEP
- Turmo Travel
- Villasimius
- CTM
- Asti
- Casale

**Riferimenti:**
- Repository: smarticket_project
- Branch: `fix/DVT-382-vendor-dashboard-purchases-v4-date-filter`
- Jira: [DVT-382](https://mimmo7.atlassian.net/browse/DVT-382)
- Gitlab Mr: [MR !215](https://gitlab.greenshare.it/arrow_to_go/smarticket_project/-/merge_requests/215)
```

**Risultato messaggio Slack:**
> **SmarTicket** - Risolto bug DVT-382 sul filtro date default in vendor_dashboard/purchases/v4 e deployato fix in produzione (v3.125.4) su tutti i vendor.

---

## Esempio 3: Task Generica

```markdown
### SmarTicket - Discussione integrazione documentazioni gestione campagne/abilitazioni

Discussione con Andrea su come integrare le nostre documentazioni relative alla gestione campagne e abilitazioni.

#### Punti Discussi

- Struttura unificata per documentazione tecnica e UX/UI
- Separazione tra developer docs e user-facing docs
- Template comuni per nuove feature

#### Prossimi Passi

- Creare struttura directory docs/
- Definire template markdown standard
- Revisionare docs esistenti
```

**Risultato messaggio Slack:**
> **SmarTicket** - Discussione con Andrea sull'integrazione documentazioni gestione campagne/abilitazioni.

---

## Esempio 4: Task con "Richiesto da"

```markdown
### Infomobile - Ottimizzazione query GTFS real-time

*-Richiesto da Domenico-*

Ottimizzate le query per il recupero dei dati GTFS real-time riducendo il carico sul database.

#### Modifiche

- Aggiunto indice composito su (feed_id, trip_id, timestamp)
- Implementato caching Redis con TTL 30 secondi
- Refactoring query N+1 in bulk query

#### Risultati

- Tempo medio di risposta ridotto da 2.3s a 0.4s
- Carico CPU database ridotto del 60%

**Riferimenti:**
- Repository: infomobile_project
- Branch: `performance/gtfs-rt-query-optimization`
- Jira: [INF-123](https://mimmo7.atlassian.net/browse/INF-123)
```

**Risultato messaggio Slack:**
> **Infomobile** - Ottimizzazione query GTFS real-time (richiesto da Domenico): ridotto tempo di risposta da 2.3s a 0.4s implementando caching Redis e indici compositi.

---

## Best Practices

### ✅ Fare

1. **Usare H3 per entry principali**: Ogni attività significativa è una entry H3
2. **Usare H4 per dettagli**: Causa del bug, Fix applicato, Deploy, Problemi identificati, ecc.
3. **Includere contesto**: Spiega brevemente cosa hai fatto e perché
4. **Menzionare chi ha richiesto**: Se applicabile, usa `*-Richiesto da {Nome}-*`
5. **Aggiungere riferimenti**: Branch, Jira, GitLab MR per tracciabilità

### ❌ Evitare

1. **NON usare H3 per dettagli tecnici**: "Causa del bug" non dovrebbe essere H3 separato
2. **NON essere troppo verboso**: Il messaggio Slack sarà conciso, mantieni il focus
3. **NON duplicare informazioni**: Se è nei riferimenti, non serve ripeterlo nel testo
4. **NON usare template entry vuoto**: `{Progetto} - {Descrizione}` va rimosso

---

## Sottosezioni H4 Riconosciute dal Parser

Il parser raggruppa automaticamente queste sezioni H3 nella entry precedente:

- `Causa del bug` / `Cause del bug`
- `Fix applicato` / `Soluzione` / `Soluzione applicata`
- `Deploy in produzione` / `Deploy` / `Deployment`
- `Implementazione` / `Testing` / `Test`
- `Modifiche` / `Changes`

**Consiglio**: Usa H4 (`####`) per queste sezioni invece di H3 (`###`), così il formato è più chiaro semanticamente.

---

## Migrazione Entry Esistenti

Se hai entry vecchie con H3 per i dettagli, NON devi modificarle manualmente. Il parser le raggrupperà automaticamente. Ma per il futuro, usa la struttura con H4 consigliata sopra.

---

## Come Verificare il Risultato

Dopo aver scritto il diario, puoi testare il messaggio generato con:

```bash
# Da Claude CLI
mcp__cronos__cronos_genera_slack_domenico
```

Il messaggio dovrebbe essere:
- Conciso (1-3 righe per progetto)
- Professionale ma amichevole
- Con dettagli rilevanti (autore MR, problemi trovati, vendor deployati)
- Senza riferimenti tecnici (branch, ticket Jira)