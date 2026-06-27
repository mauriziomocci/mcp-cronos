"""Project-identity helpers: normalization and canonical resolution.

The diary stores plain markdown; project identity is resolved at read time
against an optional [cronos.projects] registry. With an empty registry the
helpers fall back to improved parsing only (em-dash, composites), so the tool
works out-of-the-box for any user. No domain specifics live here.
"""

import re
from typing import Optional


def normalize_project(name: str) -> str:
    """Return a match key for a project name.

    Lowercases, drops parenthetical suffixes like "(v2)", and removes every
    non-alphanumeric character so that case, spacing and punctuation variants
    collapse: "WebApp"/"webapp"/"Web App" -> "webapp",
    "Auth Service"/"AuthService" -> "authservice". Genuinely different
    synonyms still need an explicit alias in the registry.
    """
    s = name.strip().lower()
    s = re.sub(r"\s*\([^)]*\)", "", s)  # drop parentheticals
    s = re.sub(r"[^0-9a-z]+", "", s)  # keep alphanumerics only
    return s


_DESC_SEP = re.compile(r"\s[-—]\s")  # " - " or " — " separating project from description


def project_tokens(heading: str) -> list[str]:
    """Split a heading's project text into one or more display project tokens.

    Composites joined by " / " become multiple tokens; the description after
    a " - " or " — " separator is dropped. Internal hyphens without surrounding
    spaces (e.g. "django-db-maintenance") are preserved.
    """
    tokens: list[str] = []
    for part in heading.split(" / "):
        token = _DESC_SEP.split(part, maxsplit=1)[0].strip()
        if token:
            tokens.append(token)
    return tokens


def canonical_projects(heading: str) -> list[str]:
    """Resolve a heading's project text to canonical project names.

    With a populated registry, only names that resolve to a known canonical are
    returned (others are dropped as unclassified). With an empty registry, the
    cleaned tokens pass through unchanged. Composites yield multiple projects.
    """
    from mcp_cronos.config import load_config  # noqa: PLC0415 — lazy to avoid import cycle

    config = load_config()
    result: list[str] = []
    for token in project_tokens(heading):
        if config.projects_registered:
            canonical = config.project_canonical.get(normalize_project(token))
            if canonical is not None and canonical not in result:
                result.append(canonical)
        else:
            if normalize_project(token) and token not in result:
                result.append(token)
    return result


def system_of(canonical: str) -> Optional[str]:
    """Return the parent system of a canonical component, or None."""
    from mcp_cronos.config import load_config  # noqa: PLC0415 — lazy to avoid import cycle

    return load_config().project_system.get(canonical)
