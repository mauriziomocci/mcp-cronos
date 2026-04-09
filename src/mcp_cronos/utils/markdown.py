"""
Utility per il parsing e la generazione di markdown del diario.

Formato file diario:
- H1 (#): Titolo "Per lo Stand-up {Data}"
- H2 (##): Sezioni "Cosa ho fatto ieri" e "Bloccanti"
- H3 (###): Entry individuali "{Progetto} - {Descrizione}"
- Separatore (---): tra le entry
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from mcp_cronos.config import load_config


@dataclass
class DiaryEntry:
    """Rappresenta una singola entry del diario."""
    progetto: str
    descrizione: str
    contenuto: str
    richiesto_da: Optional[str] = None
    riferimenti: Optional[dict] = None


@dataclass
class DiaryFile:
    """Rappresenta un file del diario completo."""
    titolo: str
    entries: list[DiaryEntry]
    bloccanti: str


def parse_diary_file(file_path: Path) -> Optional[DiaryFile]:
    """
    Legge e parsa un file del diario.

    Args:
        file_path: Path del file da leggere

    Returns:
        DiaryFile con i dati parsati, None se il file non esiste
    """
    if not file_path.exists():
        return None

    content = file_path.read_text(encoding="utf-8")
    return parse_diary_content(content)


def parse_diary_content(content: str) -> DiaryFile:
    """
    Parsa il contenuto di un file diario.

    Args:
        content: Contenuto markdown del file

    Returns:
        DiaryFile con i dati parsati
    """
    config = load_config()
    lines = content.split("\n")

    # Estrai titolo
    titolo = ""
    for line in lines:
        if line.startswith("# "):
            titolo = line[2:].strip()
            break

    # Trova sezione entries e blockers usando i nomi configurati
    entries = []
    bloccanti = config.blockers_default

    # Trova indici delle sezioni
    cosa_fatto_idx = -1
    bloccanti_idx = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"## {config.section_entries}"):
            cosa_fatto_idx = i
        elif stripped == f"## {config.section_blockers}":
            bloccanti_idx = i

    # Parsa entries
    if cosa_fatto_idx >= 0:
        end_idx = bloccanti_idx if bloccanti_idx > cosa_fatto_idx else len(lines)
        entries_content = "\n".join(lines[cosa_fatto_idx + 1:end_idx])
        entries = parse_entries(entries_content)

    # Parsa bloccanti
    if bloccanti_idx >= 0:
        bloccanti_lines = []
        for line in lines[bloccanti_idx + 1:]:
            if line.startswith("## "):
                break
            bloccanti_lines.append(line)
        bloccanti_text = "\n".join(bloccanti_lines).strip()
        if bloccanti_text:
            bloccanti = bloccanti_text

    return DiaryFile(titolo=titolo, entries=entries, bloccanti=bloccanti)


def parse_entries(content: str) -> list[DiaryEntry]:
    """
    Parsa le entry dalla sezione "Cosa ho fatto ieri".

    Raggruppa automaticamente sezioni speciali (Causa del bug, Fix applicato, ecc.)
    nella entry precedente invece di crearle come entry separate.

    Args:
        content: Contenuto della sezione

    Returns:
        Lista di DiaryEntry
    """
    # Sezioni che vanno raggruppate nella entry precedente
    SPECIAL_SECTIONS = {
        "causa del bug", "cause del bug",
        "fix applicato", "soluzione", "soluzione applicata",
        "deploy in produzione", "deploy", "deployment",
        "implementazione", "testing", "test",
        "modifiche", "changes",
    }

    entries = []

    # Split per H3 (###)
    parts = re.split(r"\n(?=### )", content)

    for part in parts:
        part = part.strip()
        if not part.startswith("### "):
            continue

        lines = part.split("\n")
        header = lines[0][4:].strip()  # Rimuovi "### "

        # Parsa header: "{Progetto} - {Descrizione}"
        if " - " in header:
            progetto, descrizione = header.split(" - ", 1)
        else:
            progetto = header
            descrizione = ""

        # Controlla se è una sezione speciale
        # Rimuovi versioni tra parentesi per il check (es. "Deploy (v1.2.3)" -> "Deploy")
        progetto_clean = re.sub(r'\s*\([^)]*\)', '', progetto).lower().strip()
        is_special = progetto_clean in SPECIAL_SECTIONS

        # Resto del contenuto
        contenuto_lines = lines[1:]

        # Cerca "Richiesto da"
        richiesto_da = None
        for line in contenuto_lines:
            match = re.match(r"\*-Richiesto da (.+)-\*", line.strip())
            if match:
                richiesto_da = match.group(1)
                break

        # Rimuovi separatore finale se presente
        contenuto = "\n".join(contenuto_lines).strip()
        if contenuto.endswith("---"):
            contenuto = contenuto[:-3].strip()

        if is_special and entries:
            # Aggiungi questa sezione al contenuto della entry precedente
            prev_entry = entries[-1]

            # Formatta come sottosezione con H4
            section_content = f"\n\n#### {progetto}\n{contenuto}"

            # Aggiungi al contenuto precedente
            entries[-1] = DiaryEntry(
                progetto=prev_entry.progetto,
                descrizione=prev_entry.descrizione,
                contenuto=prev_entry.contenuto + section_content,
                richiesto_da=prev_entry.richiesto_da,
                riferimenti=prev_entry.riferimenti
            )
        else:
            # Entry normale
            # Estrai riferimenti
            riferimenti = extract_references(contenuto)

            entries.append(DiaryEntry(
                progetto=progetto.strip(),
                descrizione=descrizione.strip(),
                contenuto=contenuto,
                richiesto_da=richiesto_da,
                riferimenti=riferimenti
            ))

    return entries


def extract_references(content: str) -> Optional[dict]:
    """
    Estrae la sezione Riferimenti dal contenuto.

    Args:
        content: Contenuto dell'entry

    Returns:
        Dict con i riferimenti trovati, None se non presenti
    """
    if "**Riferimenti:**" not in content:
        return None

    refs = {}
    in_refs = False

    for line in content.split("\n"):
        if "**Riferimenti:**" in line:
            in_refs = True
            continue
        if in_refs:
            if line.strip().startswith("- "):
                ref_line = line.strip()[2:]
                if ": " in ref_line:
                    key, value = ref_line.split(": ", 1)
                    refs[key.lower()] = value
            elif line.strip() and not line.strip().startswith("-"):
                break

    return refs if refs else None


def render_entry(entry: DiaryEntry) -> str:
    """
    Renderizza una DiaryEntry in markdown.

    Args:
        entry: Entry da renderizzare

    Returns:
        Stringa markdown
    """
    lines = []

    # Header
    if entry.descrizione:
        lines.append(f"### {entry.progetto} - {entry.descrizione}")
    else:
        lines.append(f"### {entry.progetto}")

    lines.append("")

    # Richiesto da (opzionale)
    if entry.richiesto_da:
        lines.append(f"*-Richiesto da {entry.richiesto_da}-*")
        lines.append("")

    # Contenuto
    lines.append(entry.contenuto)

    # Riferimenti (se non gia' presenti nel contenuto)
    if entry.riferimenti and "**Riferimenti:**" not in entry.contenuto:
        lines.append("")
        lines.append("**Riferimenti:**")
        for key, value in entry.riferimenti.items():
            lines.append(f"- {key.title()}: {value}")

    return "\n".join(lines)


def render_diary_file(diary: DiaryFile) -> str:
    """
    Renderizza un DiaryFile completo in markdown.

    Args:
        diary: DiaryFile da renderizzare

    Returns:
        Stringa markdown completa
    """
    lines = []

    # Titolo
    lines.append(f"# {diary.titolo}")
    lines.append("")

    # Section names from config
    config = load_config()
    lines.append(f"## {config.section_entries}")
    lines.append("")

    # Entries
    for i, entry in enumerate(diary.entries):
        lines.append(render_entry(entry))
        lines.append("")
        lines.append("---")
        lines.append("")

    # Blockers section
    lines.append(f"## {config.section_blockers}")
    lines.append("")
    lines.append(diary.bloccanti)
    lines.append("")

    return "\n".join(lines)


def extract_projects(content: str) -> list[str]:
    """
    Estrae i nomi dei progetti dalle entry.

    Args:
        content: Contenuto markdown del file

    Returns:
        Lista di nomi di progetti unici
    """
    projects = []
    for line in content.split("\n"):
        if line.startswith("### "):
            header = line[4:].strip()
            if " - " in header:
                project = header.split(" - ", 1)[0].strip()
            else:
                project = header.strip()
            if project and project not in projects:
                projects.append(project)
    return projects
