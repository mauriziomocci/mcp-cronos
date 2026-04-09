ISTRUZIONI PER IL CONSOLIDAMENTO DEL DIARIO:

Hai ricevuto il contenuto completo del diario di oggi. Il file potrebbe contenere:
- Entry separate che trattano lo stesso argomento (es. analisi iniziale + approfondimento + verifica)
- Ripetizioni di dati e conclusioni tra entry diverse
- Informazioni sparse che andrebbero raggruppate
- Sezioni aggiunte in momenti diversi senza coerenza complessiva

Il tuo compito e' riscrivere il file consolidando tutto in modo coerente.

=== REGOLE DI CONSOLIDAMENTO ===

1. RAGGRUPPA PER PROGETTO E TEMA: entry diverse sullo stesso argomento vanno fuse in una
   singola sezione. Ad esempio, "analisi ticket X", "approfondimento ticket X",
   "verifica evidenze ticket X" diventano un'unica sezione "Ticket X" con la storia
   completa dall'inizio alla fine.

2. ELIMINA RIPETIZIONI: se lo stesso dato, conclusione o evidenza appare in piu' entry,
   tienilo una sola volta nel punto piu' logico.

3. MANTIENI TUTTI I DATI: non perdere informazioni. Se un'entry contiene un URL, un ID,
   una query, un riferimento tecnico, deve restare nel file consolidato.

4. ORDINE CRONOLOGICO E LOGICO: organizza le sezioni seguendo il flusso della giornata.
   Dentro ogni sezione, racconta la storia dall'inizio alla fine, non in ordine di
   quando le entry sono state scritte.

5. FORMATO:
   - Un H3 (###) per ogni progetto/tema principale
   - Testo discorsivo, non elenchi puntati infiniti
   - Sezioni "Dove verificare" con URL e query raggruppate alla fine della sezione
   - Riferimenti (repository, branch, Jira, MR) alla fine della sezione
   - Separatore --- tra sezioni di progetti diversi

6. NON AGGIUNGERE CONTENUTO: non inventare, non interpretare, non aggiungere
   conclusioni che non erano nel diario originale. Solo riorganizzare.

7. PRESERVA LE SEZIONI DI CHIUSURA: se il diario ha gia' un "{section_day_summary}",
   "{section_tech_summary}", "{section_standup_message}", lasciali invariati.
   Se non li ha, non aggiungerli (per quelli c'e' il tool di fine giornata).

8. SEZIONE {section_blockers}: mantienila sempre alla fine.

=== PROCEDURA ===

1. Leggi tutto il contenuto
2. Identifica i temi/progetti trattati
3. Per ogni tema, raccogli tutte le informazioni sparse nel file
4. Riscrivi ogni tema come una sezione unica, coerente e completa
5. Scrivi il file consolidato al path indicato nel campo `file`
