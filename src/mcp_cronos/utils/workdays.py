"""Working-day and holiday helpers.

Determines whether a date is a public holiday (national calendar for the
configured country, plus user-defined extra holidays) and whether it is a
working day (a weekday that is not a holiday). Used by the next/previous
working-day calculations so day planning skips both weekends and holidays.
"""

from datetime import date
from typing import Optional

import holidays

from mcp_cronos.config import load_config

_national_cache: dict[str, Optional[holidays.HolidayBase]] = {}


def _national_calendar(country: str) -> Optional[holidays.HolidayBase]:
    """Return a cached national holiday calendar for the country.

    Returns None for an unsupported/unknown country code. Calendars are
    deterministic per country, so a module-level cache keyed on the country
    string is safe even when the active config changes.
    """
    if country not in _national_cache:
        try:
            _national_cache[country] = holidays.country_holidays(country)
        except NotImplementedError:
            _national_cache[country] = None
    return _national_cache[country]


def is_holiday(d: date) -> bool:
    """Return True if d is a holiday for the configured country or an extra holiday.

    Extra holidays (user-configured YYYY-MM-DD strings) are checked first. The
    national calendar comes from the `holidays` library via a per-country cache;
    an unknown country yields no national holidays and never raises, so a
    misconfiguration cannot break working-day calculation.
    """
    config = load_config()
    if d.isoformat() in set(config.calendar_extra_holidays):
        return True
    national = _national_calendar(config.calendar_country)
    return national is not None and d in national


def is_working_day(d: date) -> bool:
    """Return True if d is a weekday (Mon-Fri) and not a holiday."""
    return d.weekday() < 5 and not is_holiday(d)
