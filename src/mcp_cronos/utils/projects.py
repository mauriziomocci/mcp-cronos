"""Project-identity helpers: normalization and canonical resolution.

The diary stores plain markdown; project identity is resolved at read time
against an optional [cronos.projects] registry. With an empty registry the
helpers fall back to improved parsing only (em-dash, composites), so the tool
works out-of-the-box for any user. No domain specifics live here.
"""

import re
from typing import Optional  # noqa: F401 — used by resolvers added in the next task


def normalize_project(name: str) -> str:
    """Return a match key for a project name.

    Lowercases, drops parenthetical suffixes like "(BDI)", and removes every
    non-alphanumeric character so that case, spacing and punctuation variants
    collapse: "PayGW"/"PayGw"/"Pay GW" -> "paygw",
    "Beacon Service"/"BeaconService" -> "beaconservice". Genuinely different
    synonyms still need an explicit alias in the registry.
    """
    s = name.strip().lower()
    s = re.sub(r"\s*\([^)]*\)", "", s)  # drop parentheticals
    s = re.sub(r"[^0-9a-z]+", "", s)  # keep alphanumerics only
    return s
