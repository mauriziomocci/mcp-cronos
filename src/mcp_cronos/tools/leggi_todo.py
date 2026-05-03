"""
Tool for reading the to-do file of a specific day.

Returns the content of `todo.md` (the per-day to-do list created by
`cronos_prepara_domani`) for the requested date. By default the date is
today: the natural use case is "che dovevo fare oggi?" the morning after
the closure that seeded the file.

If a backup `todo.bak.md` exists for that date (because the to-do was
re-planned mid-day) it is reported alongside, so the caller can decide
whether to inspect the previous plan.
"""

from typing import Optional

from mcp_cronos.utils.dates import (
    get_today,
    get_todo_path,
    parse_date,
)


def leggi_todo(data: Optional[str] = None) -> dict:
    """
    Legge il file `todo.md` per la data specificata (default oggi).

    Args:
        data: Data del todo in formato YYYY-MM-DD. Se omessa, usa oggi.

    Returns:
        Dict con il contenuto markdown del todo, path del file, e
        un campo `backup` valorizzato se esiste un `todo.bak.md` da
        ripianificazione precedente. Errore se il file non esiste.
    """
    if data:
        try:
            target_date = parse_date(data)
        except ValueError as e:
            return {"errore": str(e)}
    else:
        target_date = get_today()

    todo_path = get_todo_path(target_date)
    if not todo_path.exists():
        return {
            "errore": f"todo.md non trovato per data {target_date}",
            "file": str(todo_path),
            "suggerimento": (
                "Usa cronos_prepara_domani per creare il todo della giornata, "
                "oppure verifica che la data sia corretta."
            ),
        }

    contenuto = todo_path.read_text(encoding="utf-8")

    backup_path = todo_path.parent / "todo.bak.md"
    backup_info: Optional[dict] = None
    if backup_path.exists():
        backup_info = {
            "file": str(backup_path),
            "dimensione": backup_path.stat().st_size,
        }

    return {
        "successo": True,
        "data": str(target_date),
        "file": str(todo_path),
        "contenuto": contenuto,
        "dimensione": len(contenuto),
        "backup": backup_info,
    }
