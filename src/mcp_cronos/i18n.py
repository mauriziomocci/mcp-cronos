"""
Internationalisation support for mcp-cronos.

Provides a frozen LanguagePack dataclass that bundles all locale-specific
strings used when rendering diary entries and standup messages. Two packs are
shipped — Italian ("it", the application default) and English ("en").

Design notes
------------
- LanguagePack is frozen so it can be used as a dict key or cached safely.
- list fields (months, weekdays) use a plain list rather than a tuple so
  callers can index them with the 0-based int values returned by datetime.
- format_date/format_title are thin convenience methods; heavy formatting
  logic lives in the calling modules to keep this file declarative.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class LanguagePack:
    """Locale-specific strings and formatting rules for a single language."""

    code: str
    months: list[str]  # 12 month names, index 0 = January
    weekdays: list[str]  # 7 weekday names, index 0 = Monday
    title_prefix: str  # e.g. "Per lo Stand-up"
    date_format: str  # template with {day}, {month}, {year} placeholders
    sections: dict[str, str]  # UI section labels; required keys documented below
    blockers_default: str  # default text when no blockers are present
    temporal: dict[str, str]  # relative-time expressions; required keys below

    # sections keys: entries, blockers, day_summary, tech_summary, standup_message
    # temporal keys: yesterday, day_before, last_weekday, from_to

    def format_date(self, d: date) -> str:
        """Return a human-readable date string according to this language's date_format.

        Uses 1-based day, a localised month name, and the four-digit year.
        The month index is derived from d.month (1–12) mapped to months[0–11].
        """
        return self.date_format.format(
            day=d.day,
            month=self.months[d.month - 1],
            year=d.year,
        )

    def format_title(self, standup_date: date) -> str:
        """Return the full standup title for the given date.

        Combines title_prefix with the formatted date, separated by " - ".
        """
        return f"{self.title_prefix} - {self.format_date(standup_date)}"


# ---------------------------------------------------------------------------
# Italian language pack (application default)
# ---------------------------------------------------------------------------

_IT = LanguagePack(
    code="it",
    months=[
        "Gennaio",
        "Febbraio",
        "Marzo",
        "Aprile",
        "Maggio",
        "Giugno",
        "Luglio",
        "Agosto",
        "Settembre",
        "Ottobre",
        "Novembre",
        "Dicembre",
    ],
    weekdays=["lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"],
    title_prefix="Per lo Stand-up",
    date_format="{day} {month} {year}",
    sections={
        "entries": "Cosa ho fatto ieri",
        "blockers": "Bloccanti",
        "day_summary": "Riassunto della giornata",
        "tech_summary": "Riassunto tecnico",
        "standup_message": "Messaggio per lo standup",
    },
    blockers_default="Nessuno",
    temporal={
        "yesterday": "Ieri",
        "day_before": "L'altro ieri",
        "last_weekday": "{weekday} scorso",
        "from_to": "Dal {start} al {end}",
    },
)

# ---------------------------------------------------------------------------
# English language pack
# ---------------------------------------------------------------------------

_EN = LanguagePack(
    code="en",
    months=[
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
    weekdays=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    title_prefix="For Stand-up",
    date_format="{month} {day}, {year}",
    sections={
        "entries": "What I did yesterday",
        "blockers": "Blockers",
        "day_summary": "Daily summary",
        "tech_summary": "Technical summary",
        "standup_message": "Standup message",
    },
    blockers_default="None",
    temporal={
        "yesterday": "Yesterday",
        "day_before": "Day before yesterday",
        "last_weekday": "Last {weekday}",
        "from_to": "From {start} to {end}",
    },
)

# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------

LANGUAGES: dict[str, LanguagePack] = {
    "it": _IT,
    "en": _EN,
}


def get_language_pack(lang: str) -> LanguagePack:
    """Return the LanguagePack for the given language code.

    Falls back to the Italian pack for any unrecognised or empty code, because
    Italian is the application default language.
    """
    return LANGUAGES.get(lang, _IT)
