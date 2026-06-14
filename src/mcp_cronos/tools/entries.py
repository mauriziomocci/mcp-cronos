"""
Tool for managing diary entries.

Functions:
- aggiungi_entry: Add a new entry to the diary
- imposta_bloccanti: Set or update the blockers section
"""

import re
from typing import Optional

from mcp_cronos.config import load_config
from mcp_cronos.templates import Entry, Riferimento, crea_template_vuoto
from mcp_cronos.utils.dates import (
    ensure_directory_exists,
    get_file_path,
    get_standup_title,
    get_today,
    parse_date,
)
from mcp_cronos.utils.gitinfo import detect_git_info


def aggiungi_entry(
    progetto: str,
    descrizione: str,
    paragrafo_intro: str = "",
    contenuto: str = "",
    richiesto_da: Optional[str] = None,
    repository: Optional[str] = None,
    branch: Optional[str] = None,
    jira_ticket: Optional[str] = None,
    jira_url: Optional[str] = None,
    gitlab_mr: Optional[str] = None,
    gitlab_mr_url: Optional[str] = None,
    data: Optional[str] = None,
    working_dir: Optional[str] = None,
) -> dict:
    """
    Aggiunge una nuova entry al diario di lavoro.

    Se il file non esiste, lo crea con la struttura corretta.
    Se il file esiste, aggiunge l'entry alla sezione "Cosa ho fatto ieri".

    Args:
        progetto: Nome del progetto (es. "SmarTicket", "MCP Teseo")
        descrizione: Breve descrizione del lavoro (es. "Fix bug autenticazione")
        paragrafo_intro: Paragrafo introduttivo che riassume cosa e' stato fatto (opzionale, default "")
        contenuto: Contenuto aggiuntivo (sottosezioni, bullet points, codice)
        richiesto_da: Nome della persona che ha richiesto il lavoro (opzionale)
        repository: Nome del repository (opzionale)
        branch: Nome del branch (opzionale)
        jira_ticket: Codice ticket Jira (es. "SMART-123") (opzionale)
        jira_url: URL del ticket Jira (opzionale)
        gitlab_mr: Numero MR GitLab (es. "!456") (opzionale)
        gitlab_mr_url: URL della MR GitLab (opzionale)
        data: Data del file in formato YYYY-MM-DD (opzionale, default oggi)
        working_dir: Directory git da cui rilevare repository e branch se non forniti (opzionale)

    Returns:
        Dict con risultato operazione
    """
    # Determina la data
    if data:
        try:
            file_date = parse_date(data)
        except ValueError as e:
            return {"errore": str(e)}
    else:
        file_date = get_today()

    # Auto-detect repository/branch from git when not provided explicitly.
    if repository is None or branch is None:
        det_repo, det_branch = detect_git_info(working_dir)
        repository = repository or det_repo
        branch = branch or det_branch

    # Costruisci riferimenti
    riferimenti = []
    if repository:
        riferimenti.append(Riferimento(tipo="Repository", valore=repository))
    if branch:
        riferimenti.append(Riferimento(tipo="Branch", valore=branch))
    if jira_ticket:
        riferimenti.append(Riferimento(tipo="Jira", valore=jira_ticket, url=jira_url))
    if gitlab_mr:
        riferimenti.append(
            Riferimento(
                tipo="GitLab MR",
                valore=f"MR {gitlab_mr}" if not gitlab_mr.startswith("MR") else gitlab_mr,
                url=gitlab_mr_url,
            )
        )

    # Crea l'entry
    entry = Entry(
        progetto=progetto,
        descrizione=descrizione,
        paragrafo_intro=paragrafo_intro,
        contenuto=contenuto,
        richiesto_da=richiesto_da,
        riferimenti=riferimenti,
    )

    # Ottieni il path del file
    file_path = get_file_path(file_date)

    # Assicurati che la directory esista
    ensure_directory_exists(file_path)

    # Leggi o crea il file
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        new_content = _insert_entry_in_content(content, entry)
    else:
        # Crea nuovo file con l'entry
        template = crea_template_vuoto(file_date)
        new_content = _insert_entry_in_content(template, entry)

    # Scrivi il file
    file_path.write_text(new_content, encoding="utf-8")

    return {
        "successo": True,
        "file": str(file_path),
        "data": str(file_date),
        "titolo_standup": get_standup_title(file_date),
        "progetto": progetto,
        "descrizione": descrizione,
        "messaggio": f"Entry aggiunta al diario per {file_date}",
    }


def _insert_entry_in_content(content: str, entry: Entry) -> str:
    """
    Inserisce un'entry nel contenuto del file diario.

    L'entry viene inserita alla fine della sezione "Cosa ho fatto ieri",
    prima della sezione "Bloccanti".

    Args:
        content: Contenuto attuale del file
        entry: Entry da inserire

    Returns:
        Contenuto aggiornato
    """
    config = load_config()
    bloccanti_pattern = f"\n## {re.escape(config.section_blockers)}\n"

    # Find the position of the blockers section
    bloccanti_match = re.search(bloccanti_pattern, content)

    if bloccanti_match:
        # Insert before the blockers section
        insert_pos = bloccanti_match.start()

        # Generate entry markdown
        entry_md = entry.to_markdown()

        # Insert with separator
        new_content = content[:insert_pos] + "\n" + entry_md + "\n\n---\n" + content[insert_pos:]
    else:
        # No blockers section found -- append at end and add one
        entry_md = entry.to_markdown()
        new_content = (
            content.rstrip() + "\n\n" + entry_md + "\n\n---\n\n"
            f"## {config.section_blockers}\n\n{config.blockers_default}\n"
        )

    return new_content


def imposta_bloccanti(
    bloccanti: str,
    data: Optional[str] = None,
) -> dict:
    """
    Imposta o aggiorna la sezione Bloccanti del diario.

    Args:
        bloccanti: Testo dei bloccanti (usa "Nessuno" se non ci sono bloccanti)
        data: Data del file in formato YYYY-MM-DD (opzionale, default oggi)

    Returns:
        Dict con risultato operazione
    """
    # Determina la data
    if data:
        try:
            file_date = parse_date(data)
        except ValueError as e:
            return {"errore": str(e)}
    else:
        file_date = get_today()

    # Ottieni il path del file
    file_path = get_file_path(file_date)

    if not file_path.exists():
        return {
            "errore": f"File non trovato per data {file_date}",
            "suggerimento": "Usa aggiungi_entry per creare il file prima di impostare i bloccanti",
        }

    # Leggi il contenuto
    content = file_path.read_text(encoding="utf-8")

    # Update the blockers section using the configured section name
    config = load_config()
    escaped_section = re.escape(config.section_blockers)
    pattern = rf"(## {escaped_section}\n\n).*?(?=\n## |\Z)"
    replacement = f"\\1{bloccanti}\n"

    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)

    if count == 0:
        # No blockers section found -- append one
        new_content = content.rstrip() + f"\n\n## {config.section_blockers}\n\n{bloccanti}\n"

    # Scrivi il file
    file_path.write_text(new_content, encoding="utf-8")

    return {
        "successo": True,
        "file": str(file_path),
        "data": str(file_date),
        "bloccanti": bloccanti,
        "messaggio": f"Bloccanti aggiornati per {file_date}",
    }
