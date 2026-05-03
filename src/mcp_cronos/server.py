"""
MCP Server per la gestione del diario di lavoro.

Server MCP (Model Context Protocol) che espone tool per:
- Aggiungere entry al diario giornaliero
- Aggiungere contenuto a entry di progetto esistenti
- Leggere entry per data o range
- Generare riassunti discorsivi per lo stand-up
- Cercare testo nelle entry
- Generare riassunti settimanali
- Gestire bloccanti
- Elencare progetti menzionati
- Chiudere la giornata con riassunti e consolidamento

Configurazione:
    Variabile d'ambiente CRONOS_DIARIO_PATH (obbligatoria): path del diario

Utilizzo:
    mcp-cronos                    # Avvia il server
    python -m mcp_cronos.server   # Alternativa
"""

import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from mcp_cronos.tools.aggiungi_progetto import aggiungi_a_progetto
from mcp_cronos.tools.cerca import cerca_nel_diario
from mcp_cronos.tools.consolida import consolida_diario

# Import tool
from mcp_cronos.tools.entries import aggiungi_entry, imposta_bloccanti
from mcp_cronos.tools.fine_giornata import fine_giornata
from mcp_cronos.tools.prepara_domani import prepara_domani
from mcp_cronos.tools.reader import leggi_diario, lista_progetti
from mcp_cronos.tools.scrivi_fine_giornata import scrivi_fine_giornata
from mcp_cronos.tools.settimana import riassunto_settimana
from mcp_cronos.tools.standup import genera_riassunto_standup

# Crea server MCP
server = Server("mcp-cronos")


# ============================================================================
# DEFINIZIONE TOOL
# ============================================================================

TOOLS = [
    Tool(
        name="cronos_aggiungi_entry",
        description="""Aggiunge una nuova entry al diario di lavoro.

Se il file non esiste, lo crea con la struttura corretta.
Il titolo del file segue il formato "Per lo Stand-up {Giorno+1} {Mese} {Anno}".

Parametri:
- progetto (str, required): Nome del progetto (es. "SmarTicket", "MCP Teseo")
- descrizione (str, required): Breve descrizione del lavoro (es. "Fix bug autenticazione")
- paragrafo_intro (str, required): Paragrafo introduttivo che riassume cosa e' stato fatto
- contenuto (str, optional): Contenuto aggiuntivo (sottosezioni, bullet points, codice)
- richiesto_da (str, optional): Nome della persona che ha richiesto il lavoro
- repository (str, optional): Nome del repository
- branch (str, optional): Nome del branch
- jira_ticket (str, optional): Codice ticket Jira (es. "SMART-123")
- jira_url (str, optional): URL del ticket Jira
- gitlab_mr (str, optional): Numero MR GitLab (es. "!456")
- gitlab_mr_url (str, optional): URL della MR GitLab
- data (str, optional): Data del file YYYY-MM-DD (default: oggi)

Restituisce: Conferma dell'operazione con path del file e dettagli.""",
        inputSchema={
            "type": "object",
            "properties": {
                "progetto": {"type": "string", "description": "Nome del progetto"},
                "descrizione": {"type": "string", "description": "Breve descrizione del lavoro"},
                "paragrafo_intro": {"type": "string", "description": "Paragrafo introduttivo"},
                "contenuto": {"type": "string", "description": "Contenuto aggiuntivo (opzionale)"},
                "richiesto_da": {
                    "type": "string",
                    "description": "Nome di chi ha richiesto il lavoro (opzionale)",
                },
                "repository": {"type": "string", "description": "Nome del repository (opzionale)"},
                "branch": {"type": "string", "description": "Nome del branch (opzionale)"},
                "jira_ticket": {"type": "string", "description": "Codice ticket Jira (opzionale)"},
                "jira_url": {"type": "string", "description": "URL del ticket Jira (opzionale)"},
                "gitlab_mr": {"type": "string", "description": "Numero MR GitLab (opzionale)"},
                "gitlab_mr_url": {
                    "type": "string",
                    "description": "URL della MR GitLab (opzionale)",
                },
                "data": {
                    "type": "string",
                    "description": "Data YYYY-MM-DD (opzionale, default oggi)",
                },
            },
            "required": ["progetto", "descrizione", "paragrafo_intro"],
        },
    ),
    Tool(
        name="cronos_leggi_diario",
        description="""Legge il contenuto del diario per una data o range di date.

Modalita' di utilizzo (mutualmente esclusive):
1. data: Legge un singolo giorno
2. data_inizio + data_fine: Legge un range di date
3. ultimi_giorni: Legge gli ultimi N giorni
4. Nessun parametro: Legge il diario di oggi

Parametri:
- data (str, optional): Data singola YYYY-MM-DD
- data_inizio (str, optional): Data inizio range YYYY-MM-DD
- data_fine (str, optional): Data fine range YYYY-MM-DD
- ultimi_giorni (int, optional): Numero di giorni da leggere

Restituisce: Contenuto del diario con entries, progetti e bloccanti.""",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data singola YYYY-MM-DD"},
                "data_inizio": {"type": "string", "description": "Data inizio range YYYY-MM-DD"},
                "data_fine": {"type": "string", "description": "Data fine range YYYY-MM-DD"},
                "ultimi_giorni": {"type": "integer", "description": "Numero di giorni da leggere"},
            },
        },
    ),
    Tool(
        name="cronos_imposta_bloccanti",
        description="""Imposta o aggiorna la sezione Bloccanti del diario.

Il file deve esistere (usa cronos_aggiungi_entry per crearlo).

Parametri:
- bloccanti (str, required): Testo dei bloccanti ("Nessuno" se non ci sono bloccanti)
- data (str, optional): Data del file YYYY-MM-DD (default: oggi)

Restituisce: Conferma dell'operazione con path del file.""",
        inputSchema={
            "type": "object",
            "properties": {
                "bloccanti": {"type": "string", "description": "Testo dei bloccanti"},
                "data": {
                    "type": "string",
                    "description": "Data YYYY-MM-DD (opzionale, default oggi)",
                },
            },
            "required": ["bloccanti"],
        },
    ),
    Tool(
        name="cronos_riassunto_standup",
        description="""Genera un riassunto discorsivo del diario per lo standup.

Restituisce il contenuto completo delle entry del diario insieme a istruzioni
di stile per generare un messaggio alto livello, fluido e professionale.

Stile del riassunto:
- Alto livello, niente dettagli implementativi
- Fluido e naturale, frasi discorsive, no elenchi puntati
- Niente numeri di MR, codici Jira, nomi di file o classi
- Niente strumenti interni (MCP, tool CLI, script)
- Dettagli tecnici solo se interessanti per decisioni future

Usa questo tool quando l'utente chiede:
- Un riassunto per lo standup / stand-up
- "Cosa dico allo standup?"
- "Riassumi cosa ho fatto [data]"
- "Fammi un riassunto discorsivo"

Parametri:
- data (str, optional): Data singola YYYY-MM-DD (default: ultimo giorno lavorativo)
- data_inizio (str, optional): Data inizio range YYYY-MM-DD
- data_fine (str, optional): Data fine range YYYY-MM-DD

Restituisce: Contenuto del diario con istruzioni di stile per la generazione del messaggio.""",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data singola YYYY-MM-DD"},
                "data_inizio": {"type": "string", "description": "Data inizio range YYYY-MM-DD"},
                "data_fine": {"type": "string", "description": "Data fine range YYYY-MM-DD"},
            },
        },
    ),
    Tool(
        name="cronos_fine_giornata",
        description="""Chiusura di fine giornata: legge le entry del diario e restituisce istruzioni per ristrutturarle.

Usa questo tool quando l'utente dice:
- "Fine giornata" / "Chiudi la giornata"
- "Riscrivi il diario"
- "Genera i riassunti di fine giornata"
- "Fai il wrap-up della giornata"

Il tool restituisce le entry grezze del giorno insieme a istruzioni dettagliate
per generare quattro output:
1. Entry riscritte in ordine cronologico e logico
2. Riassunto della giornata (paragrafo narrativo)
3. Riassunto tecnico (denso, con tutti i dettagli implementativi)
4. Messaggio per lo standup (alto livello, discorsivo)

Parametri:
- data (str, optional): Data YYYY-MM-DD (default: oggi)

Restituisce: Entry del diario con istruzioni di stile per la generazione.""",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "Data YYYY-MM-DD (opzionale, default oggi)",
                }
            },
        },
    ),
    Tool(
        name="cronos_consolida_diario",
        description="""Consolida il diario rileggendolo e riscrivendolo in modo coerente.

Utile quando il diario ha entry separate sullo stesso argomento, ripetizioni,
o informazioni sparse che andrebbero raggruppate. Il tool rilegge il file,
identifica i problemi di struttura, e restituisce istruzioni per riscriverlo.

Usa questo tool quando l'utente dice:
- "Consolida il diario"
- "Riscrivi il diario in modo coerente"
- "Elimina le ripetizioni dal diario"
- "Organizza meglio il diario"
- "Unifica le entry del diario"

Parametri:
- data (str, optional): Data YYYY-MM-DD (default: oggi)

Restituisce: Contenuto del file con analisi e istruzioni per il consolidamento.""",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "Data YYYY-MM-DD (opzionale, default oggi)",
                }
            },
        },
    ),
    Tool(
        name="cronos_lista_progetti",
        description="""Elenca i progetti menzionati nel diario in un periodo.

Utile per avere una panoramica dei progetti su cui si e' lavorato.

Parametri:
- data_inizio (str, optional): Data inizio YYYY-MM-DD
- data_fine (str, optional): Data fine YYYY-MM-DD
- ultimi_giorni (int, optional): Se non specificate le date, usa gli ultimi N giorni (default 30)

Restituisce: Lista progetti con occorrenze e date.""",
        inputSchema={
            "type": "object",
            "properties": {
                "data_inizio": {"type": "string", "description": "Data inizio YYYY-MM-DD"},
                "data_fine": {"type": "string", "description": "Data fine YYYY-MM-DD"},
                "ultimi_giorni": {
                    "type": "integer",
                    "description": "Giorni da analizzare (default 30)",
                },
            },
        },
    ),
    Tool(
        name="cronos_cerca",
        description="""Cerca testo nelle entry del diario.

Ricerca full-text case-insensitive con supporto regex.
Utile per trovare quando si e' lavorato su un progetto, ticket, argomento.

Usa questo tool quando l'utente chiede:
- "Quando ho lavorato su X?"
- "Cerca nel diario Y"
- "Trova il ticket Z"
- "In quali giorni ho toccato il progetto W?"

Parametri:
- query (str, required): Testo da cercare (case-insensitive, supporta regex)
- data_inizio (str, optional): Data inizio range YYYY-MM-DD
- data_fine (str, optional): Data fine range YYYY-MM-DD
- ultimi_giorni (int, optional): Giorni da cercare (default 90)

Restituisce: Lista di match con data, progetto, contesto.""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Testo da cercare (supporta regex)"},
                "data_inizio": {"type": "string", "description": "Data inizio YYYY-MM-DD"},
                "data_fine": {"type": "string", "description": "Data fine YYYY-MM-DD"},
                "ultimi_giorni": {
                    "type": "integer",
                    "description": "Giorni da cercare (default 90)",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="cronos_settimana",
        description="""Riassunto settimanale del diario raggruppato per progetto.

Mostra su quanti giorni si e' lavorato per ogni progetto durante la settimana,
con riepilogo delle attivita'. Utile per report settimanali o per capire
la distribuzione del lavoro.

Usa questo tool quando l'utente chiede:
- "Cosa ho fatto questa settimana?"
- "Riassunto settimanale"
- "Su cosa ho lavorato questa settimana?"
- "Report della settimana"

Parametri:
- data (str, optional): Una data nella settimana da analizzare YYYY-MM-DD (default: settimana corrente)

Restituisce: Riassunto per progetto con giorni, date e attivita'.""",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "Data nella settimana YYYY-MM-DD (default: corrente)",
                }
            },
        },
    ),
    Tool(
        name="cronos_aggiungi_a_progetto",
        description="""Aggiunge contenuto a un'entry di progetto esistente nel diario.

Se nel diario di oggi esiste gia' un'entry per il progetto specificato,
aggiunge una sotto-sezione (H4) evitando frammentazione. Se non esiste,
crea una nuova entry standard.

Usa questo tool quando:
- L'utente aggiunge lavoro su un progetto gia' presente nel diario di oggi
- "Aggiungi al progetto X che ho fatto anche Y"
- "Ho continuato su X, aggiungi..."

Per una nuova entry su un progetto nuovo, usa cronos_aggiungi_entry.

Parametri:
- progetto (str, required): Nome esatto del progetto (deve corrispondere all'H3 esistente)
- titolo_fase (str, required): Titolo della sotto-sezione (es. "Fix bug login")
- contenuto (str, required): Contenuto della sotto-sezione
- richiesto_da (str, optional): Chi ha richiesto il lavoro
- repository (str, optional): Nome del repository
- branch (str, optional): Nome del branch
- jira_ticket (str, optional): Codice ticket Jira
- jira_url (str, optional): URL del ticket Jira
- gitlab_mr (str, optional): Numero MR GitLab
- gitlab_mr_url (str, optional): URL della MR GitLab
- data (str, optional): Data YYYY-MM-DD (default: oggi)

Restituisce: Conferma con modalita' (aggiunto_a_esistente o nuova_entry).""",
        inputSchema={
            "type": "object",
            "properties": {
                "progetto": {"type": "string", "description": "Nome esatto del progetto"},
                "titolo_fase": {"type": "string", "description": "Titolo della sotto-sezione"},
                "contenuto": {"type": "string", "description": "Contenuto della sotto-sezione"},
                "richiesto_da": {
                    "type": "string",
                    "description": "Chi ha richiesto il lavoro (opzionale)",
                },
                "repository": {"type": "string", "description": "Nome del repository (opzionale)"},
                "branch": {"type": "string", "description": "Nome del branch (opzionale)"},
                "jira_ticket": {"type": "string", "description": "Codice ticket Jira (opzionale)"},
                "jira_url": {"type": "string", "description": "URL del ticket Jira (opzionale)"},
                "gitlab_mr": {"type": "string", "description": "Numero MR GitLab (opzionale)"},
                "gitlab_mr_url": {
                    "type": "string",
                    "description": "URL della MR GitLab (opzionale)",
                },
                "data": {"type": "string", "description": "Data YYYY-MM-DD (default: oggi)"},
            },
            "required": ["progetto", "titolo_fase", "contenuto"],
        },
    ),
    Tool(
        name="cronos_scrivi_fine_giornata",
        description="""Scrive il file di fine giornata con il contenuto generato.

Usa questo tool DOPO cronos_fine_giornata: prima generi il contenuto
seguendo le istruzioni ricevute, poi chiami questo tool per scriverlo.

Parametri:
- contenuto (str, required): Contenuto markdown completo del file
- data (str, optional): Data YYYY-MM-DD (default: oggi)

Restituisce: Conferma con path del file scritto.""",
        inputSchema={
            "type": "object",
            "properties": {
                "contenuto": {
                    "type": "string",
                    "description": "Contenuto markdown completo del file",
                },
                "data": {"type": "string", "description": "Data YYYY-MM-DD (default: oggi)"},
            },
            "required": ["contenuto"],
        },
    ),
    Tool(
        name="cronos_prepara_domani",
        description="""Prepara la cartella del prossimo giorno lavorativo con todo.md e scheletro raw.md.

Default: il giorno target e' calcolato come prossimo giorno lavorativo da oggi
(lun-gio -> +1, ven -> lun, sab -> lun, dom -> lun). In alternativa si puo'
specificare una data esplicita per pianificare un giorno futuro qualsiasi.

Comportamento:
- Crea/sovrascrive `todo.md` con `contenuto_todo` (un to-do e' l'ultima
  pianificazione, non un log progressivo).
- Crea `raw.md` con lo scheletro standard SOLO se non esiste gia', per non
  sovrascrivere entry aggiunte in anticipo.

Usa questo tool:
- Al termine di `cronos_scrivi_fine_giornata`, per impostare il todo del
  giorno successivo a partire dai punti aperti della giornata.
- Manualmente quando vuoi pianificare le cose da fare in un giorno futuro.

Parametri:
- contenuto_todo (str, required): Contenuto markdown completo di todo.md
- data (str, optional): Data target YYYY-MM-DD (default: prossimo giorno lavorativo)

Restituisce: Conferma con path di todo.md e raw.md, e flag se raw e' stato creato.""",
        inputSchema={
            "type": "object",
            "properties": {
                "contenuto_todo": {
                    "type": "string",
                    "description": "Contenuto markdown completo del file todo.md",
                },
                "data": {
                    "type": "string",
                    "description": (
                        "Data target YYYY-MM-DD (opzionale, default: prossimo "
                        "giorno lavorativo)"
                    ),
                },
            },
            "required": ["contenuto_todo"],
        },
    ),
]


# ============================================================================
# HANDLER TOOL
# ============================================================================


@server.list_tools()
async def list_tools():
    """Restituisce la lista dei tool disponibili."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Esegue un tool con gli argomenti forniti."""

    try:
        result = None

        if name == "cronos_aggiungi_entry":
            result = aggiungi_entry(
                progetto=arguments["progetto"],
                descrizione=arguments["descrizione"],
                paragrafo_intro=arguments["paragrafo_intro"],
                contenuto=arguments.get("contenuto", ""),
                richiesto_da=arguments.get("richiesto_da"),
                repository=arguments.get("repository"),
                branch=arguments.get("branch"),
                jira_ticket=arguments.get("jira_ticket"),
                jira_url=arguments.get("jira_url"),
                gitlab_mr=arguments.get("gitlab_mr"),
                gitlab_mr_url=arguments.get("gitlab_mr_url"),
                data=arguments.get("data"),
            )

        elif name == "cronos_leggi_diario":
            result = leggi_diario(
                data=arguments.get("data"),
                data_inizio=arguments.get("data_inizio"),
                data_fine=arguments.get("data_fine"),
                ultimi_giorni=arguments.get("ultimi_giorni"),
            )

        elif name == "cronos_imposta_bloccanti":
            result = imposta_bloccanti(
                bloccanti=arguments["bloccanti"],
                data=arguments.get("data"),
            )

        elif name == "cronos_riassunto_standup":
            result = genera_riassunto_standup(
                data=arguments.get("data"),
                data_inizio=arguments.get("data_inizio"),
                data_fine=arguments.get("data_fine"),
            )

        elif name == "cronos_fine_giornata":
            result = fine_giornata(
                data=arguments.get("data"),
            )

        elif name == "cronos_consolida_diario":
            result = consolida_diario(
                data=arguments.get("data"),
            )

        elif name == "cronos_lista_progetti":
            result = lista_progetti(
                data_inizio=arguments.get("data_inizio"),
                data_fine=arguments.get("data_fine"),
                ultimi_giorni=arguments.get("ultimi_giorni", 30),
            )

        elif name == "cronos_cerca":
            result = cerca_nel_diario(
                query=arguments["query"],
                data_inizio=arguments.get("data_inizio"),
                data_fine=arguments.get("data_fine"),
                ultimi_giorni=arguments.get("ultimi_giorni", 90),
            )

        elif name == "cronos_settimana":
            result = riassunto_settimana(
                data=arguments.get("data"),
            )

        elif name == "cronos_aggiungi_a_progetto":
            result = aggiungi_a_progetto(
                progetto=arguments["progetto"],
                titolo_fase=arguments["titolo_fase"],
                contenuto=arguments["contenuto"],
                richiesto_da=arguments.get("richiesto_da"),
                repository=arguments.get("repository"),
                branch=arguments.get("branch"),
                jira_ticket=arguments.get("jira_ticket"),
                jira_url=arguments.get("jira_url"),
                gitlab_mr=arguments.get("gitlab_mr"),
                gitlab_mr_url=arguments.get("gitlab_mr_url"),
                data=arguments.get("data"),
            )

        elif name == "cronos_scrivi_fine_giornata":
            result = scrivi_fine_giornata(
                contenuto=arguments["contenuto"],
                data=arguments.get("data"),
            )

        elif name == "cronos_prepara_domani":
            result = prepara_domani(
                contenuto_todo=arguments["contenuto_todo"],
                data=arguments.get("data"),
            )

        else:
            result = {"errore": f"Tool '{name}' non riconosciuto"}

        # Formatta output come JSON
        return [
            TextContent(
                type="text", text=json.dumps(result, indent=2, ensure_ascii=False, default=str)
            )
        ]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"errore": str(e)}, ensure_ascii=False))]


# ============================================================================
# MAIN
# ============================================================================


async def main():
    """Entry point principale del server MCP."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run():
    """Funzione wrapper per entry point."""
    import asyncio

    asyncio.run(main())


if __name__ == "__main__":
    run()
