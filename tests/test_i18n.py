"""
Tests for the i18n module.

Covers language registration, data integrity, formatting methods,
and fallback behaviour for unknown language codes.
"""

from datetime import date

import pytest

from mcp_cronos.i18n import LANGUAGES, LanguagePack, get_language_pack

REQUIRED_SECTION_KEYS = {
    "entries", "blockers", "day_summary", "tech_summary", "standup_message",
    "references", "requested_by",
}
REQUIRED_TEMPORAL_KEYS = {"yesterday", "day_before", "last_weekday", "from_to"}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_languages_registered():
    """Both 'it' and 'en' must be present in LANGUAGES."""
    assert "it" in LANGUAGES
    assert "en" in LANGUAGES


def test_languages_are_language_pack_instances():
    """Every value in LANGUAGES must be a LanguagePack instance."""
    for lang, pack in LANGUAGES.items():
        assert isinstance(pack, LanguagePack), f"LANGUAGES['{lang}'] is not a LanguagePack"


# ---------------------------------------------------------------------------
# get_language_pack
# ---------------------------------------------------------------------------


def test_get_language_pack_it():
    pack = get_language_pack("it")
    assert pack.code == "it"


def test_get_language_pack_en():
    pack = get_language_pack("en")
    assert pack.code == "en"


def test_get_language_pack_unknown_falls_back_to_italian():
    """An unrecognised language code must fall back to Italian."""
    pack = get_language_pack("xx")
    assert pack.code == "it"


def test_get_language_pack_empty_string_falls_back_to_italian():
    pack = get_language_pack("")
    assert pack.code == "it"


# ---------------------------------------------------------------------------
# Italian pack — data integrity
# ---------------------------------------------------------------------------


class TestItalianPack:
    @pytest.fixture(autouse=True)
    def pack(self):
        self.pack = get_language_pack("it")

    def test_code(self):
        assert self.pack.code == "it"

    def test_months_count(self):
        assert len(self.pack.months) == 12

    def test_months_values(self):
        expected = [
            "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
        ]
        assert self.pack.months == expected

    def test_weekdays_count(self):
        assert len(self.pack.weekdays) == 7

    def test_weekdays_values(self):
        expected = ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"]
        assert self.pack.weekdays == expected

    def test_title_prefix(self):
        assert self.pack.title_prefix == "Per lo Stand-up"

    def test_date_format(self):
        assert self.pack.date_format == "{day} {month} {year}"

    def test_sections_keys(self):
        assert set(self.pack.sections.keys()) == REQUIRED_SECTION_KEYS

    def test_sections_values(self):
        assert self.pack.sections["entries"] == "Cosa ho fatto ieri"
        assert self.pack.sections["blockers"] == "Bloccanti"
        assert self.pack.sections["day_summary"] == "Riassunto della giornata"
        assert self.pack.sections["tech_summary"] == "Riassunto tecnico"
        assert self.pack.sections["standup_message"] == "Messaggio per lo standup"
        assert self.pack.sections["references"] == "Riferimenti"
        assert self.pack.sections["requested_by"] == "Richiesto da"

    def test_blockers_default(self):
        assert self.pack.blockers_default == "Nessuno"

    def test_temporal_keys(self):
        assert set(self.pack.temporal.keys()) == REQUIRED_TEMPORAL_KEYS

    def test_temporal_values(self):
        assert self.pack.temporal["yesterday"] == "Ieri"
        assert self.pack.temporal["day_before"] == "L'altro ieri"
        assert self.pack.temporal["last_weekday"] == "{weekday} scorso"
        assert self.pack.temporal["from_to"] == "Dal {start} al {end}"

    def test_format_date(self):
        d = date(2026, 4, 9)
        result = self.pack.format_date(d)
        assert result == "9 Aprile 2026"

    def test_format_date_january(self):
        d = date(2026, 1, 1)
        result = self.pack.format_date(d)
        assert result == "1 Gennaio 2026"

    def test_format_title(self):
        d = date(2026, 4, 9)
        result = self.pack.format_title(d)
        assert result == "Per lo Stand-up - 9 Aprile 2026"


# ---------------------------------------------------------------------------
# English pack — data integrity
# ---------------------------------------------------------------------------


class TestEnglishPack:
    @pytest.fixture(autouse=True)
    def pack(self):
        self.pack = get_language_pack("en")

    def test_code(self):
        assert self.pack.code == "en"

    def test_months_count(self):
        assert len(self.pack.months) == 12

    def test_months_values(self):
        expected = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        assert self.pack.months == expected

    def test_weekdays_count(self):
        assert len(self.pack.weekdays) == 7

    def test_weekdays_values(self):
        expected = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        assert self.pack.weekdays == expected

    def test_title_prefix(self):
        assert self.pack.title_prefix == "For Stand-up"

    def test_date_format(self):
        assert self.pack.date_format == "{month} {day}, {year}"

    def test_sections_keys(self):
        assert set(self.pack.sections.keys()) == REQUIRED_SECTION_KEYS

    def test_sections_values(self):
        assert self.pack.sections["entries"] == "What I did yesterday"
        assert self.pack.sections["blockers"] == "Blockers"
        assert self.pack.sections["day_summary"] == "Daily summary"
        assert self.pack.sections["tech_summary"] == "Technical summary"
        assert self.pack.sections["standup_message"] == "Standup message"
        assert self.pack.sections["references"] == "References"
        assert self.pack.sections["requested_by"] == "Requested by"

    def test_blockers_default(self):
        assert self.pack.blockers_default == "None"

    def test_temporal_keys(self):
        assert set(self.pack.temporal.keys()) == REQUIRED_TEMPORAL_KEYS

    def test_temporal_values(self):
        assert self.pack.temporal["yesterday"] == "Yesterday"
        assert self.pack.temporal["day_before"] == "Day before yesterday"
        assert self.pack.temporal["last_weekday"] == "Last {weekday}"
        assert self.pack.temporal["from_to"] == "From {start} to {end}"

    def test_format_date(self):
        d = date(2026, 4, 9)
        result = self.pack.format_date(d)
        assert result == "April 9, 2026"

    def test_format_date_january(self):
        d = date(2026, 1, 1)
        result = self.pack.format_date(d)
        assert result == "January 1, 2026"

    def test_format_title(self):
        d = date(2026, 4, 9)
        result = self.pack.format_title(d)
        assert result == "For Stand-up - April 9, 2026"


# ---------------------------------------------------------------------------
# LanguagePack immutability
# ---------------------------------------------------------------------------


def test_language_pack_is_frozen():
    """LanguagePack must be immutable (frozen dataclass)."""
    pack = get_language_pack("it")
    with pytest.raises((AttributeError, TypeError)):
        pack.code = "xx"  # type: ignore[misc]
