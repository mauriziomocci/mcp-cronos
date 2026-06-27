"""
Tool for end-of-day diary closure.

Reads the raw entries for the day and returns instructions for:
1. Rewriting them in chronological/logical order
2. Generating a day summary
3. Generating a technical summary
4. Generating a standup message

The LLM generates the four outputs and writes the complete file directly.
"""

from typing import Optional

from mcp_cronos.config import load_config
from mcp_cronos.template_loader import load_template
from mcp_cronos.utils.dates import get_file_path, get_standup_title, get_today, parse_date
from mcp_cronos.utils.markdown import parse_diary_file


def _get_style_instructions() -> str:
    """Load the end-of-day template and replace section placeholders with config values.

    Uses manual string replacement instead of str.format() because the template
    contains other brace-delimited placeholders (e.g. {titolo_standup}) that are
    part of the instruction text and must not be expanded.
    """
    config = load_config()
    template = load_template("fine_giornata")
    replacements = {
        "{section_entries}": config.section_entries,
        "{section_blockers}": config.section_blockers,
        "{section_day_summary}": config.section_day_summary,
        "{section_tech_summary}": config.section_tech_summary,
        "{section_standup_message}": config.section_standup_message,
    }
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


def fine_giornata(
    data: Optional[str] = None,
) -> dict:
    """
    Prepara i dati per la chiusura di fine giornata.

    Legge le entry del giorno e restituisce il contenuto completo
    insieme alle istruzioni di stile per generare i quattro output
    e scrivere il file definitivo.

    Args:
        data: Data del diario in formato YYYY-MM-DD (default: oggi)

    Returns:
        Dict con entries, istruzioni, path del file e metadati
    """
    if data:
        try:
            file_date = parse_date(data)
        except ValueError as e:
            return {"errore": str(e)}
    else:
        file_date = get_today()

    file_path = get_file_path(file_date)

    if not file_path.exists():
        return {
            "errore": f"File non trovato per data {file_date}",
            "file": str(file_path),
            "suggerimento": "Usa cronos_aggiungi_entry per creare il file e aggiungere entry durante la giornata",
        }

    diary = parse_diary_file(file_path)
    contenuto_grezzo = file_path.read_text(encoding="utf-8")

    # Supporta sia il formato strutturato (con entry parsate)
    # sia il formato libero (consolidato manualmente, senza sezione
    # "Cosa ho fatto ieri" o entry con formato ### Progetto - Descrizione)
    if diary and diary.entries:
        # Raggruppa entry dello stesso progetto per evitare frammentazione
        entries = _consolida_entries(diary.entries)

        return {
            "istruzioni": _get_style_instructions(),
            "data": str(file_date),
            "file": str(file_path),
            "titolo_standup": get_standup_title(file_date),
            "entries": entries,
            "bloccanti": diary.bloccanti if diary else "Nessuno",
            "num_entries": len(entries),
            "progetti": list(dict.fromkeys(e["progetto"] for e in entries)),
        }

    # Free-form format: file exists but has no parseable entries.
    config = load_config()
    blockers_header = f"## {config.section_blockers}"
    progetti = []
    bloccanti = config.blockers_default
    for line in contenuto_grezzo.split("\n"):
        stripped = line.strip()
        if stripped.startswith("### "):
            header = stripped[4:].strip()
            progetto = header.split(" - ")[0].split(" — ")[0].strip()
            if progetto and progetto not in progetti:
                progetti.append(progetto)
        if stripped == blockers_header:
            idx = contenuto_grezzo.index(blockers_header)
            bloccanti_text = contenuto_grezzo[idx + len(blockers_header) :].strip()
            next_h2 = bloccanti_text.find("\n## ")
            if next_h2 > 0:
                bloccanti_text = bloccanti_text[:next_h2].strip()
            if bloccanti_text:
                bloccanti = bloccanti_text

    return {
        "istruzioni": _get_style_instructions(),
        "data": str(file_date),
        "file": str(file_path),
        "titolo_standup": get_standup_title(file_date),
        "formato": "libero",
        "nota": (
            "Il diario non ha il formato standard con sezione "
            "'Cosa ho fatto ieri' e entry ### Progetto - Descrizione. "
            "Viene fornito il contenuto completo del file. "
            "Leggilo, identifica le sezioni logiche, e genera "
            "i quattro output di fine giornata."
        ),
        "contenuto_completo": contenuto_grezzo,
        "bloccanti": bloccanti,
        "progetti": progetti,
    }


def _consolida_entries(entries) -> list[dict]:
    """
    Raggruppa entry dello stesso progetto in un'unica entry consolidata.

    Se ci sono 3 entry per "Backend API", le unisce in una sola con il contenuto
    concatenato. Le descrizioni vengono combinate e il contenuto separato
    da sotto-sezioni.
    """
    progetti_visti = {}
    risultato = []

    for entry in entries:
        proj = entry.progetto
        entry_data = {
            "progetto": proj,
            "descrizione": entry.descrizione,
            "contenuto_completo": entry.contenuto,
            "richiesto_da": entry.richiesto_da,
        }

        if proj not in progetti_visti:
            progetti_visti[proj] = len(risultato)
            risultato.append(entry_data)
        else:
            # Progetto già visto: consolida
            idx = progetti_visti[proj]
            esistente = risultato[idx]

            # Combina descrizioni se diverse
            if entry.descrizione and entry.descrizione != esistente["descrizione"]:
                esistente["descrizione"] += f" / {entry.descrizione}"

            # Aggiungi contenuto come sotto-sezione
            separatore = (
                f"\n\n--- entry successiva: {entry.descrizione} ---\n\n"
                if entry.descrizione
                else "\n\n"
            )
            esistente["contenuto_completo"] += separatore + entry.contenuto

            # Preserva richiesto_da se non già presente
            if entry.richiesto_da and not esistente["richiesto_da"]:
                esistente["richiesto_da"] = entry.richiesto_da

    return risultato
