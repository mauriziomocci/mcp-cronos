"""
Tool for preparing the next working day's folder.

Creates the per-day folder of the target date with two files:
- `todo.md`: lista cose da fare nella giornata (sovrascritto se gia' presente)
- `raw.md`: scheletro vuoto del log giornaliero (creato solo se non esiste,
  per non perdere entry gia' aggiunte in anticipo)

Default behaviour: target date is the next working day calculated from today
(Mon-Thu -> +1, Fri -> Mon, Sat -> Mon, Sun -> Mon), so calling this from the
end-of-day flow on a Friday correctly skips the weekend.
"""

from typing import Optional

from mcp_cronos.templates import crea_template_vuoto
from mcp_cronos.utils.dates import (
    ensure_directory_exists,
    get_next_working_day,
    get_raw_path,
    get_today,
    get_todo_path,
    parse_date,
)


def prepara_domani(
    contenuto_todo: str,
    data: Optional[str] = None,
) -> dict:
    """
    Prepara la cartella del prossimo giorno lavorativo (o di una data esplicita).

    Crea/aggiorna i file nella cartella della data target:
    - `todo.md`: scritto con `contenuto_todo`. Se esiste gia' un todo
      precedente per quella data, viene salvato come `todo.bak.md`
      prima della sovrascrittura, per non perdere annotazioni manuali.
    - `raw.md`: scheletro markdown vuoto generato dal template standard. Viene
      creato solo se il file NON esiste, per non sovrascrivere entry gia'
      aggiunte in anticipo per quella data.

    Args:
        contenuto_todo: Contenuto markdown completo del file todo.md.
        data: Data target opzionale in formato YYYY-MM-DD. Se omessa,
              viene usato il prossimo giorno lavorativo a partire da oggi.

    Returns:
        Dict con conferma operazione, path dei file scritti e flag che
        indicano se raw e' stato creato e se il todo precedente e' stato
        salvato in backup.
    """
    if data:
        try:
            target_date = parse_date(data)
        except ValueError as e:
            return {"errore": str(e)}
    else:
        target_date = get_next_working_day(get_today())

    todo_path = get_todo_path(target_date)
    raw_path = get_raw_path(target_date)
    backup_path = todo_path.parent / "todo.bak.md"

    ensure_directory_exists(todo_path)

    backup_creato = False
    if todo_path.exists():
        backup_path.write_text(todo_path.read_text(encoding="utf-8"), encoding="utf-8")
        backup_creato = True

    todo_path.write_text(contenuto_todo, encoding="utf-8")

    raw_creato_adesso = False
    if not raw_path.exists():
        ensure_directory_exists(raw_path)
        raw_path.write_text(crea_template_vuoto(target_date), encoding="utf-8")
        raw_creato_adesso = True

    if raw_creato_adesso:
        raw_msg = "creato"
    else:
        raw_msg = "gia presente, lasciato intatto"

    if backup_creato:
        todo_msg = "sovrascritto (precedente in todo.bak.md)"
    else:
        todo_msg = "creato"

    return {
        "successo": True,
        "data": str(target_date),
        "todo_file": str(todo_path),
        "raw_file": str(raw_path),
        "backup_file": str(backup_path) if backup_creato else None,
        "raw_creato_adesso": raw_creato_adesso,
        "todo_backup_creato": backup_creato,
        "dimensione_todo": len(contenuto_todo),
        "messaggio": (
            f"Cartella preparata per {target_date}: "
            f"todo.md {todo_msg}, raw.md {raw_msg}."
        ),
    }
