"""
Tool for appending content to an existing project entry.

If a diary entry for the same project already exists today, appends an H4
sub-section instead of creating a new entry. If none exists, creates a new
standard entry.
"""

import re
from typing import Optional

from mcp_cronos.config import load_config
from mcp_cronos.templates import crea_template_vuoto
from mcp_cronos.utils.dates import ensure_directory_exists, get_file_path, get_today, parse_date
from mcp_cronos.utils.gitinfo import detect_git_info


def aggiungi_a_progetto(
    progetto: str,
    titolo_fase: str,
    contenuto: str,
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
    Aggiunge contenuto a un'entry di progetto esistente o ne crea una nuova.

    Se esiste gia' un'entry per il progetto specificato, aggiunge una
    sotto-sezione H4. Se non esiste, crea una nuova entry standard.

    Args:
        progetto: Nome del progetto (deve corrispondere esattamente)
        titolo_fase: Titolo della sotto-sezione (es. "Fix bug login", "Deploy v1.2.3")
        contenuto: Contenuto della sotto-sezione
        richiesto_da: Chi ha richiesto il lavoro (opzionale)
        repository: Nome del repository (opzionale)
        branch: Nome del branch (opzionale)
        jira_ticket: Codice ticket Jira (opzionale)
        jira_url: URL del ticket Jira (opzionale)
        gitlab_mr: Numero MR GitLab (opzionale)
        gitlab_mr_url: URL della MR GitLab (opzionale)
        data: Data del file YYYY-MM-DD (default: oggi)
        working_dir: Directory git da cui rilevare repository e branch se non forniti (opzionale)

    Returns:
        Dict con risultato operazione
    """
    if data:
        try:
            file_date = parse_date(data)
        except ValueError as e:
            return {"errore": str(e)}
    else:
        file_date = get_today()

    file_path = get_file_path(file_date)
    ensure_directory_exists(file_path)

    # Auto-detect repository/branch from git when not provided explicitly.
    if repository is None or branch is None:
        det_repo, det_branch = detect_git_info(working_dir)
        repository = repository or det_repo
        branch = branch or det_branch

    riferimenti_lines = _build_riferimenti_lines(
        repository, branch, jira_ticket, jira_url, gitlab_mr, gitlab_mr_url
    )

    if not file_path.exists():
        return _crea_nuova_entry(
            file_path, file_date, progetto, titolo_fase, contenuto, richiesto_da, riferimenti_lines
        )

    file_content = file_path.read_text(encoding="utf-8")

    # Cerca entry esistente per questo progetto
    pattern = re.compile(
        rf"^### {re.escape(progetto)}\s*-\s*(.+)$",
        re.MULTILINE,
    )
    match = pattern.search(file_content)

    if match:
        return _aggiungi_fase(
            file_path,
            file_content,
            match,
            progetto,
            titolo_fase,
            contenuto,
            richiesto_da,
            riferimenti_lines,
        )
    else:
        return _crea_nuova_entry(
            file_path, file_date, progetto, titolo_fase, contenuto, richiesto_da, riferimenti_lines
        )


def _build_riferimenti_lines(repository, branch, jira_ticket, jira_url, gitlab_mr, gitlab_mr_url):
    """Costruisce le righe markdown dei riferimenti."""
    lines = []
    if repository:
        lines.append(f"- Repository: {repository}")
    if branch:
        lines.append(f"- Branch: `{branch}`")
    if jira_ticket:
        if jira_url:
            lines.append(f"- Jira: [{jira_ticket}]({jira_url})")
        else:
            lines.append(f"- Jira: {jira_ticket}")
    if gitlab_mr:
        mr_label = f"MR {gitlab_mr}" if not gitlab_mr.startswith("MR") else gitlab_mr
        if gitlab_mr_url:
            lines.append(f"- GitLab MR: [{mr_label}]({gitlab_mr_url})")
        else:
            lines.append(f"- GitLab MR: {mr_label}")
    return lines


def _aggiungi_fase(
    file_path,
    file_content,
    match,
    progetto,
    titolo_fase,
    contenuto,
    richiesto_da,
    riferimenti_lines,
):
    """Aggiunge una sotto-sezione H4 a un'entry esistente."""
    # Find the end of the current entry
    config = load_config()
    escaped_blockers = re.escape(config.section_blockers)
    rest = file_content[match.end() :]
    end_pattern = re.search(rf"\n(?=### |\n## {escaped_blockers})", rest)
    if end_pattern:
        insert_pos = match.end() + end_pattern.start()
    else:
        bloccanti_match = re.search(rf"\n## {escaped_blockers}", file_content)
        if bloccanti_match:
            insert_pos = bloccanti_match.start()
        else:
            insert_pos = len(file_content)

    # Costruisci la sotto-sezione
    fase_lines = [f"\n\n#### {titolo_fase}\n"]
    if richiesto_da:
        fase_lines.append(f"*-{config.section_requested_by} {richiesto_da}-*\n")
    fase_lines.append(contenuto)
    if riferimenti_lines:
        fase_lines.append(f"\n**{config.section_references}:**")
        fase_lines.extend(riferimenti_lines)

    fase_md = "\n".join(fase_lines)

    new_content = file_content[:insert_pos] + fase_md + file_content[insert_pos:]
    file_path.write_text(new_content, encoding="utf-8")

    return {
        "successo": True,
        "file": str(file_path),
        "data": str(file_path.stem[:10]),
        "progetto": progetto,
        "fase": titolo_fase,
        "modalita": "aggiunto_a_esistente",
        "messaggio": f"Fase '{titolo_fase}' aggiunta all'entry '{progetto}'",
    }


def _crea_nuova_entry(
    file_path, file_date, progetto, titolo_fase, contenuto, richiesto_da, riferimenti_lines
):
    """Crea una nuova entry con il contenuto come prima fase."""
    config = load_config()
    lines = [f"### {progetto} - {titolo_fase}\n"]
    if richiesto_da:
        lines.append(f"*-{config.section_requested_by} {richiesto_da}-*\n")
    lines.append(contenuto)
    if riferimenti_lines:
        lines.append(f"\n**{config.section_references}:**")
        lines.extend(riferimenti_lines)

    entry_md = "\n".join(lines)

    if file_path.exists():
        file_content = file_path.read_text(encoding="utf-8")
    else:
        file_content = crea_template_vuoto(file_date)

    escaped_blockers = re.escape(config.section_blockers)
    bloccanti_match = re.search(rf"\n## {escaped_blockers}\n", file_content)
    if bloccanti_match:
        insert_pos = bloccanti_match.start()
        new_content = (
            file_content[:insert_pos] + "\n" + entry_md + "\n\n---\n" + file_content[insert_pos:]
        )
    else:
        new_content = (
            file_content.rstrip() + "\n\n" + entry_md + "\n\n---\n\n"
            f"## {config.section_blockers}\n\n{config.blockers_default}\n"
        )

    file_path.write_text(new_content, encoding="utf-8")

    return {
        "successo": True,
        "file": str(file_path),
        "data": str(file_date),
        "progetto": progetto,
        "fase": titolo_fase,
        "modalita": "nuova_entry",
        "messaggio": f"Nuova entry creata per '{progetto}'",
    }
