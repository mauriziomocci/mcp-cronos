"""
Configuration for MCP Cronos.

Loads settings from a cronos.toml file (searched in priority order: explicit
CRONOS_CONFIG_PATH env var, diary root, ~/.config/cronos/) and merges them with
language-specific defaults from the i18n module.

The diary path is still provided by the original helper functions, which are kept
as-is because other modules import them directly.
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

from mcp_cronos.i18n import get_language_pack

# ---------------------------------------------------------------------------
# Diary path helpers (unchanged — other modules depend on these)
# ---------------------------------------------------------------------------


def get_diario_path() -> Path:
    """
    Return the diary root path from the CRONOS_DIARIO_PATH environment variable.

    Returns:
        Path to the diary working directory.

    Raises:
        RuntimeError: If CRONOS_DIARIO_PATH is not set.
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
    Check whether the diary directory exists.

    Returns:
        True if the directory exists, False otherwise.
    """
    return get_diario_path().exists()


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------


@dataclass
class CronosConfig:
    """Full application configuration, merged from TOML file and language defaults."""

    lang: str
    section_entries: str
    section_blockers: str
    section_day_summary: str
    section_tech_summary: str
    section_standup_message: str
    section_references: str
    section_requested_by: str
    calendar_country: str
    calendar_extra_holidays: list[str]
    blockers_default: str
    title_format: str
    git_enabled: bool
    auto_push: bool
    commit_message: str


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_config: Optional[CronosConfig] = None


def _reset_config() -> None:
    """
    Clear the cached CronosConfig singleton.

    Intended exclusively for tests that need to reload config between cases.
    Should not be called in production code.
    """
    global _config
    _config = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_config_file() -> Optional[Path]:
    """
    Search for a cronos.toml file in priority order.

    Search order:
    1. CRONOS_CONFIG_PATH env var (explicit path, highest priority)
    2. {CRONOS_DIARIO_PATH}/cronos.toml
    3. ~/.config/cronos/cronos.toml

    Returns the first existing Path found, or None if none exist.
    """
    explicit = os.environ.get("CRONOS_CONFIG_PATH")
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p

    # Diary root — only attempt if CRONOS_DIARIO_PATH is set (avoid RuntimeError)
    diario_env = os.environ.get("CRONOS_DIARIO_PATH")
    if diario_env:
        candidate = Path(diario_env) / "cronos.toml"
        if candidate.exists():
            return candidate

    # XDG-style user config
    xdg = Path.home() / ".config" / "cronos" / "cronos.toml"
    if xdg.exists():
        return xdg

    return None


def _parse_toml(path: Path) -> dict[str, Any]:
    """
    Parse a TOML file and return its contents as a dict.

    Returns an empty dict on any error (missing file, invalid syntax, missing
    tomllib/tomli library) so that callers can always fall back to defaults
    without special-casing the error.
    """
    if tomllib is None:
        return {}
    try:
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    except Exception:  # noqa: BLE001 — intentional catch-all for TOML parse errors
        return {}


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------


def load_config() -> CronosConfig:
    """
    Load, merge, and cache the application configuration.

    Resolution order for each setting:
    - Explicit user value in cronos.toml beats language default.
    - Language defaults come from get_language_pack(lang).
    - Hard-coded fallbacks apply when neither source provides a value.

    The result is cached in the module-level _config singleton. Call
    _reset_config() to force a fresh load (useful in tests).

    Returns:
        A fully populated CronosConfig instance.
    """
    global _config
    if _config is not None:
        return _config

    # Parse the config file (empty dict if not found or unreadable)
    config_path = _find_config_file()
    raw: dict[str, Any] = _parse_toml(config_path) if config_path is not None else {}

    cronos_section: dict[str, Any] = raw.get("cronos", {})

    # Language
    lang: str = cronos_section.get("lang", "it")
    pack = get_language_pack(lang)

    # Section names: user overrides > language defaults
    user_sections: dict[str, Any] = cronos_section.get("sections", {})
    section_entries = user_sections.get("entries", pack.sections["entries"])
    section_blockers = user_sections.get("blockers", pack.sections["blockers"])
    section_day_summary = user_sections.get("day_summary", pack.sections["day_summary"])
    section_tech_summary = user_sections.get("tech_summary", pack.sections["tech_summary"])
    section_standup_message = user_sections.get("standup_message", pack.sections["standup_message"])
    section_references = user_sections.get("references", pack.sections["references"])
    section_requested_by = user_sections.get("requested_by", pack.sections["requested_by"])

    # Diary settings
    user_diary: dict[str, Any] = cronos_section.get("diary", {})
    title_format: str = user_diary.get("title_format", f"{pack.title_prefix} - {{date}}")

    # Git settings: user overrides > defaults.
    # The [cronos] section may carry a top-level scalar `git = false/true` as a
    # shorthand for git_enabled, or a full [cronos.git] sub-table. Both forms
    # are supported; the sub-table form takes precedence when present.
    raw_git = cronos_section.get("git", {})
    if isinstance(raw_git, dict):
        user_git: dict[str, Any] = raw_git
        git_enabled_default: bool = True
    else:
        # Scalar shorthand: `git = false` under [cronos]
        user_git = {}
        git_enabled_default = bool(raw_git)
    git_enabled: bool = bool(user_git.get("enabled", git_enabled_default))
    auto_push: bool = bool(user_git.get("auto_push", True))
    commit_message: str = user_git.get("commit_message", "diario: fine giornata {date}")

    # Calendar settings: national-holiday country code + user extra holidays.
    user_calendar: dict[str, Any] = cronos_section.get("calendar", {})
    calendar_country: str = user_calendar.get("country", "IT")
    raw_extra = user_calendar.get("extra_holidays", [])
    calendar_extra_holidays: list[str] = (
        [str(x) for x in raw_extra] if isinstance(raw_extra, list) else []
    )

    _config = CronosConfig(
        lang=lang,
        section_entries=section_entries,
        section_blockers=section_blockers,
        section_day_summary=section_day_summary,
        section_tech_summary=section_tech_summary,
        section_standup_message=section_standup_message,
        section_references=section_references,
        section_requested_by=section_requested_by,
        calendar_country=calendar_country,
        calendar_extra_holidays=calendar_extra_holidays,
        blockers_default=pack.blockers_default,
        title_format=title_format,
        git_enabled=git_enabled,
        auto_push=auto_push,
        commit_message=commit_message,
    )
    return _config
