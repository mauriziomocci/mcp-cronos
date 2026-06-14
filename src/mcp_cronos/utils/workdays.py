"""Working-day and holiday helpers.

Determines whether a date is a public holiday (national calendar for the
configured country, plus user-defined extra holidays) and whether it is a
working day (a weekday that is not a holiday). Used by the next/previous
working-day calculations so day planning skips both weekends and holidays.
"""

from datetime import date

import holidays

from mcp_cronos.config import load_config


def is_holiday(d: date) -> bool:
    """Return True if d is a holiday for the configured country or an extra holiday.

    The national calendar comes from the `holidays` library, which expands years
    on demand. Extra holidays are user-configured YYYY-MM-DD strings. An unknown
    or unsupported country code falls back to extra holidays only and never
    raises, so a misconfiguration cannot break working-day calculation.
    """
    config = load_config()
    if d.isoformat() in set(config.calendar_extra_holidays):
        return True
    try:
        national = holidays.country_holidays(config.calendar_country)
    except (KeyError, NotImplementedError):
        return False
    return d in national


def is_working_day(d: date) -> bool:
    """Return True if d is a weekday (Mon-Fri) and not a holiday."""
    return d.weekday() < 5 and not is_holiday(d)
