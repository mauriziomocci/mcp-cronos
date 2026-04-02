# MCP Cronos

Server MCP (Model Context Protocol) per la gestione del diario di lavoro giornaliero.

## Funzionalita'

- **Aggiunta entry**: Aggiunge nuove entry al diario, creando automaticamente file e cartelle
- **Lettura diario**: Legge entry per data singola o range di date
- **Messaggi Slack**: Genera messaggi Slack per Domenico nello stile definito
- **Gestione bloccanti**: Imposta e aggiorna la sezione bloccanti
- **Lista progetti**: Elenca i progetti su cui si e' lavorato in un periodo

## Installazione

```bash
cd /Users/mauriziomocci/Documents/workspace/MCP/Cronos
uv sync
```

## Configurazione Claude Code

Aggiungi a `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "cronos": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/mauriziomocci/Documents/workspace/MCP/Cronos",
        "run",
        "mcp-cronos"
      ],
      "env": {
        "CRONOS_DIARIO_PATH": "/Users/mauriziomocci/Documents/workspace/Diario"
      }
    }
  }
}
```

## Tool Disponibili

### `cronos_aggiungi_entry`

Aggiunge una nuova entry al diario di lavoro.

**Parametri:**
- `progetto` (required): Nome del progetto
- `descrizione` (required): Breve descrizione del lavoro
- `paragrafo_intro` (required): Paragrafo introduttivo
- `contenuto`: Contenuto aggiuntivo (opzionale)
- `richiesto_da`: Nome di chi ha richiesto il lavoro (opzionale)
- `repository`: Nome del repository (opzionale)
- `branch`: Nome del branch (opzionale)
- `jira_ticket`: Codice ticket Jira (opzionale)
- `jira_url`: URL del ticket Jira (opzionale)
- `gitlab_mr`: Numero MR GitLab (opzionale)
- `gitlab_mr_url`: URL della MR GitLab (opzionale)
- `data`: Data YYYY-MM-DD (opzionale, default oggi)

### `cronos_leggi_diario`

Legge il contenuto del diario.

**Parametri:**
- `data`: Data singola YYYY-MM-DD
- `data_inizio`, `data_fine`: Range di date
- `ultimi_giorni`: Numero di giorni da leggere

### `cronos_genera_slack_domenico`

Genera un messaggio Slack per Domenico.

**Parametri:**
- `data`: Data singola YYYY-MM-DD (default: ieri)
- `data_inizio`, `data_fine`: Range di date

### `cronos_imposta_bloccanti`

Imposta la sezione Bloccanti del diario.

**Parametri:**
- `bloccanti` (required): Testo dei bloccanti
- `data`: Data YYYY-MM-DD (opzionale, default oggi)

### `cronos_lista_progetti`

Elenca i progetti menzionati nel diario.

**Parametri:**
- `data_inizio`, `data_fine`: Range di date
- `ultimi_giorni`: Giorni da analizzare (default 30)

## Struttura Directory Diario

```
Diario/
├── CLAUDE.md
├── docs/
└── {anno}/
    └── {mese}/
        └── {anno}-{mese}-{giorno}.md
```

## Formato File

Il file del diario segue il formato:

```markdown
# Per lo Stand-up {Giorno+1} {Mese} {Anno}

## Cosa ho fatto ieri

### {Progetto} - {Descrizione}

{Paragrafo introduttivo}

**Sottosezione:**
- Punto 1
- Punto 2

**Riferimenti:**
- Repository: nome
- Branch: `branch`
- Jira: [TICKET](url)
- GitLab MR: [MR !123](url)

---

## Bloccanti

Nessuno
```

## Test

```bash
# Avvia il server manualmente
uv run mcp-cronos

# Esegui i test
uv run pytest
```

## Licenza

MIT