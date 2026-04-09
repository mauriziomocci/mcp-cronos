"""
Tool per scrivere il file di fine giornata.

Riceve il contenuto markdown generato dall'LLM dopo cronos_fine_giornata
e lo scrive al file del diario corretto. After writing, commits and pushes
the changes to the diary git repository.
"""

import subprocess
from typing import Optional

from mcp_cronos.config import get_diario_path
from mcp_cronos.utils.dates import get_file_path, get_today, parse_date, ensure_directory_exists


def _git_commit_and_push(file_path, file_date) -> dict:
    """
    Stages, commits, and pushes the diary file to the remote repository.

    Runs git commands in the diary root directory (CRONOS_DIARIO_PATH).
    Returns a dict with git operation results.

    Args:
        file_path: Absolute path of the file to commit
        file_date: Date of the diary entry (used in commit message)

    Returns:
        Dict with git operation status and details
    """
    diario_root = str(get_diario_path())
    relative_path = str(file_path.relative_to(diario_root))

    git_result = {"git_add": None, "git_commit": None, "git_push": None}

    try:
        # git add
        subprocess.run(
            ["git", "add", relative_path],
            cwd=diario_root,
            capture_output=True,
            text=True,
            check=True,
        )
        git_result["git_add"] = "ok"

        # git commit
        commit_msg = f"diario: fine giornata {file_date}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=diario_root,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            git_result["git_commit"] = "ok"
        elif "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
            git_result["git_commit"] = "nessuna modifica da committare"
            return git_result
        else:
            git_result["git_commit"] = f"errore: {result.stderr.strip()}"
            return git_result

        # git push
        result = subprocess.run(
            ["git", "push"],
            cwd=diario_root,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            git_result["git_push"] = "ok"
        else:
            git_result["git_push"] = f"errore: {result.stderr.strip()}"

    except FileNotFoundError:
        git_result["git_add"] = "errore: git non trovato"
    except subprocess.CalledProcessError as e:
        git_result["git_add"] = f"errore: {e.stderr.strip()}"

    return git_result


def scrivi_fine_giornata(
    contenuto: str,
    data: Optional[str] = None,
) -> dict:
    """
    Writes the end-of-day file and commits/pushes it to the diary repository.

    Args:
        contenuto: Contenuto markdown completo del file (con tutte le sezioni)
        data: Data del file YYYY-MM-DD (default: oggi)

    Returns:
        Dict con risultato operazione e stato git
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

    file_path.write_text(contenuto, encoding="utf-8")

    # Commit and push to diary repository
    git_result = _git_commit_and_push(file_path, file_date)

    return {
        "successo": True,
        "file": str(file_path),
        "data": str(file_date),
        "dimensione": len(contenuto),
        "messaggio": f"File di fine giornata scritto per {file_date}",
        "git": git_result,
    }
