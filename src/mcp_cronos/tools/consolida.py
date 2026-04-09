"""
Tool for diary consolidation.

Re-reads the diary file, identifies logical sections, and returns the full
content with LLM instructions on how to rewrite it -- removing repetitions,
merging entries that cover the same topic, and organising everything into
a coherent logical structure.

Useful when the diary was written during the day with separate entries that
should be unified, or when it contains repetitions from successive updates
on the same topic.
"""

from typing import Optional

from mcp_cronos.config import load_config
from mcp_cronos.template_loader import load_template
from mcp_cronos.utils.dates import get_file_path, get_standup_title, get_today, parse_date


def _get_style_instructions() -> str:
    """Load the consolidation template and replace section placeholders with config values.

    Uses manual string replacement instead of str.format() because the template
    may contain other brace-delimited text that must not be expanded.
    """
    config = load_config()
    template = load_template("consolida")
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


def consolida_diario(
    data: Optional[str] = None,
) -> dict:
    """
    Rilegge il diario e restituisce il contenuto con istruzioni per consolidarlo.

    Il tool non modifica il file direttamente. Restituisce il contenuto completo
    e le istruzioni per l'LLM, che dovra' riscrivere il file eliminando
    ripetizioni e organizzando le sezioni in modo logico.

    Args:
        data: Data del diario in formato YYYY-MM-DD (default: oggi)

    Returns:
        Dict con contenuto del file, istruzioni e metadati
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
        }

    contenuto = file_path.read_text(encoding="utf-8")

    if not contenuto.strip():
        return {
            "errore": f"File vuoto per data {file_date}",
            "file": str(file_path),
        }

    # Analisi del contenuto per identificare potenziali problemi
    lines = contenuto.split("\n")
    h3_sections = [ln.strip() for ln in lines if ln.strip().startswith("### ")]
    h2_sections = [ln.strip() for ln in lines if ln.strip().startswith("## ")]

    # Identifica progetti dai titoli H3
    progetti = []
    for h3 in h3_sections:
        header = h3[4:].strip()
        progetto = header.split(" - ")[0].split(" — ")[0].strip()
        progetti.append(progetto)

    # Conta occorrenze per progetto per identificare duplicati
    from collections import Counter

    progetto_count = Counter(progetti)
    duplicati = {p: c for p, c in progetto_count.items() if c > 1}

    # Calcola dimensione file
    num_righe = len(lines)
    num_sezioni_h3 = len(h3_sections)

    return {
        "istruzioni": _get_style_instructions(),
        "data": str(file_date),
        "file": str(file_path),
        "titolo_standup": get_standup_title(file_date),
        "contenuto_completo": contenuto,
        "analisi": {
            "num_righe": num_righe,
            "num_sezioni_h3": num_sezioni_h3,
            "sezioni_h2": h2_sections,
            "sezioni_h3": h3_sections,
            "progetti_trovati": list(progetto_count.keys()),
            "progetti_con_entry_multiple": duplicati if duplicati else None,
        },
        "suggerimenti": _genera_suggerimenti(duplicati, num_sezioni_h3, h3_sections),
    }


def _genera_suggerimenti(duplicati: dict, num_sezioni: int, sezioni: list) -> list:
    """Genera suggerimenti per il consolidamento basati sull'analisi."""
    suggerimenti = []

    if duplicati:
        for progetto, count in duplicati.items():
            suggerimenti.append(
                f"Il progetto '{progetto}' ha {count} sezioni separate — "
                f"probabilmente vanno unificate in una sola"
            )

    if num_sezioni > 8:
        suggerimenti.append(
            f"Il diario ha {num_sezioni} sezioni H3 — valuta se alcune "
            f"possono essere raggruppate per tema"
        )

    # Cerca pattern di entry incrementali (analisi, approfondimento, verifica)
    incrementali = [
        "approfondimento",
        "verifica",
        "aggiornamento",
        "follow-up",
        "correzione",
        "conferma",
        "dettaglio",
    ]
    for sez in sezioni:
        sez_lower = sez.lower()
        for pattern in incrementali:
            if pattern in sez_lower:
                suggerimenti.append(
                    f"La sezione '{sez[4:]}' sembra un aggiornamento di una "
                    f"sezione precedente — valuta se integrarla"
                )
                break

    if not suggerimenti:
        suggerimenti.append("Nessun problema evidente rilevato nel formato")

    return suggerimenti
