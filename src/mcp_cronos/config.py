"""
Configurazione per MCP Cronos.

Il path del diario viene letto dalla variabile d'ambiente CRONOS_DIARIO_PATH.
La variabile e' obbligatoria.
"""

import os
from pathlib import Path


def get_diario_path() -> Path:
    """
    Restituisce il path del diario.

    Legge dalla variabile d'ambiente CRONOS_DIARIO_PATH.

    Returns:
        Path del diario di lavoro

    Raises:
        RuntimeError: Se CRONOS_DIARIO_PATH non e' impostata
    """
    path_str = os.environ.get("CRONOS_DIARIO_PATH")
    if not path_str:
        raise RuntimeError(
            "Variabile d'ambiente CRONOS_DIARIO_PATH non impostata. "
            "Imposta il path del diario di lavoro, es: "
            "CRONOS_DIARIO_PATH=/path/to/Diario"
        )
    return Path(path_str)


def ensure_diario_exists() -> bool:
    """
    Verifica che il path del diario esista.

    Returns:
        True se esiste, False altrimenti
    """
    return get_diario_path().exists()