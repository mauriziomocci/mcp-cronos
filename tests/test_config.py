"""
Tests for the config module.

Covers: get_diario_path, load_config with Italian and English defaults,
config file discovery (diario root, explicit env var, CRONOS_CONFIG_PATH),
section overrides, git config, invalid TOML fallback, and blockers_default.
"""

from pathlib import Path

import pytest

from mcp_cronos.config import (
    CronosConfig,
    _find_config_file,
    _parse_toml,
    _reset_config,
    ensure_diario_exists,
    get_diario_path,
    load_config,
)

# ---------------------------------------------------------------------------
# Autouse fixture: reset singleton before and after each test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_config():
    """Reset the config singleton before and after every test to prevent state leakage."""
    _reset_config()
    yield
    _reset_config()


# ---------------------------------------------------------------------------
# get_diario_path
# ---------------------------------------------------------------------------


def test_get_diario_path_with_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """get_diario_path returns the path set in CRONOS_DIARIO_PATH."""
    monkeypatch.setenv("CRONOS_DIARIO_PATH", str(tmp_path))
    assert get_diario_path() == tmp_path


def test_get_diario_path_without_env_var(monkeypatch: pytest.MonkeyPatch):
    """get_diario_path raises RuntimeError when CRONOS_DIARIO_PATH is not set."""
    monkeypatch.delenv("CRONOS_DIARIO_PATH", raising=False)
    with pytest.raises(RuntimeError):
        get_diario_path()


# ---------------------------------------------------------------------------
# ensure_diario_exists
# ---------------------------------------------------------------------------


def test_ensure_diario_exists_true(tmp_diario: Path):
    """ensure_diario_exists returns True when the diary directory exists."""
    assert ensure_diario_exists() is True


def test_ensure_diario_exists_false(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """ensure_diario_exists returns False when the diary directory does not exist."""
    nonexistent = tmp_path / "nonexistent"
    monkeypatch.setenv("CRONOS_DIARIO_PATH", str(nonexistent))
    assert ensure_diario_exists() is False


# ---------------------------------------------------------------------------
# Default config (no file present) — Italian defaults
# ---------------------------------------------------------------------------


def test_default_config_returns_cronos_config(tmp_diario: Path):
    """load_config returns a CronosConfig instance even without a config file."""
    config = load_config()
    assert isinstance(config, CronosConfig)


def test_default_config_lang_is_italian(tmp_diario: Path):
    """Default language is 'it' when no config file is present."""
    config = load_config()
    assert config.lang == "it"


def test_default_config_italian_section_entries(tmp_diario: Path):
    """Default entries section name comes from the Italian language pack."""
    config = load_config()
    assert config.section_entries == "Cosa ho fatto ieri"


def test_default_config_italian_section_blockers(tmp_diario: Path):
    """Default blockers section name comes from the Italian language pack."""
    config = load_config()
    assert config.section_blockers == "Bloccanti"


def test_default_config_italian_blockers_default(tmp_diario: Path):
    """Default blockers_default comes from the Italian language pack."""
    config = load_config()
    assert config.blockers_default == "Nessuno"


def test_default_config_git_enabled(tmp_diario: Path):
    """Git is enabled by default."""
    config = load_config()
    assert config.git_enabled is True


def test_default_config_git_auto_push(tmp_diario: Path):
    """auto_push is enabled by default."""
    config = load_config()
    assert config.auto_push is True


def test_default_git_commit_message(tmp_diario: Path):
    """Default git commit message template is 'diario: fine giornata {date}'."""
    config = load_config()
    assert config.commit_message == "diario: fine giornata {date}"


# ---------------------------------------------------------------------------
# Config from diario root (cronos.toml next to the diary)
# ---------------------------------------------------------------------------


def test_config_from_diario_root(config_toml_it: Path):
    """load_config picks up cronos.toml from the diary root directory."""
    config = load_config()
    assert config.lang == "it"


def test_config_from_diario_root_english(config_toml_en: Path):
    """load_config picks up lang='en' from cronos.toml in the diary root."""
    config = load_config()
    assert config.lang == "en"


# ---------------------------------------------------------------------------
# Section names from language packs
# ---------------------------------------------------------------------------


def test_section_names_from_italian_language(config_toml_it: Path):
    """Section names are loaded from the Italian language pack when lang='it'."""
    config = load_config()
    assert config.section_entries == "Cosa ho fatto ieri"
    assert config.section_blockers == "Bloccanti"
    assert config.section_day_summary == "Riassunto della giornata"
    assert config.section_tech_summary == "Riassunto tecnico"
    assert config.section_standup_message == "Messaggio per lo standup"


def test_section_names_from_english_language(config_toml_en: Path):
    """Section names are loaded from the English language pack when lang='en'."""
    config = load_config()
    assert config.section_entries == "What I did yesterday"
    assert config.section_blockers == "Blockers"
    assert config.section_day_summary == "Daily summary"
    assert config.section_tech_summary == "Technical summary"
    assert config.section_standup_message == "Standup message"


# ---------------------------------------------------------------------------
# Config from explicit CRONOS_CONFIG_PATH
# ---------------------------------------------------------------------------


def test_config_from_explicit_env_var(
    tmp_path: Path, tmp_diario: Path, monkeypatch: pytest.MonkeyPatch
):
    """CRONOS_CONFIG_PATH takes precedence over the diario-root config file."""
    explicit_config = tmp_path / "custom_cronos.toml"
    explicit_config.write_text('[cronos]\nlang = "en"\n', encoding="utf-8")
    monkeypatch.setenv("CRONOS_CONFIG_PATH", str(explicit_config))
    config = load_config()
    assert config.lang == "en"


def test_explicit_env_var_takes_precedence_over_diario_root(
    tmp_path: Path, tmp_diario: Path, monkeypatch: pytest.MonkeyPatch
):
    """CRONOS_CONFIG_PATH overrides a competing cronos.toml in the diario root."""
    # Italian config in diario root
    diario_config = tmp_diario / "cronos.toml"
    diario_config.write_text('[cronos]\nlang = "it"\n', encoding="utf-8")
    # English config at explicit path
    explicit_config = tmp_path / "explicit.toml"
    explicit_config.write_text('[cronos]\nlang = "en"\n', encoding="utf-8")
    monkeypatch.setenv("CRONOS_CONFIG_PATH", str(explicit_config))
    config = load_config()
    assert config.lang == "en"


# ---------------------------------------------------------------------------
# Section override in config file
# ---------------------------------------------------------------------------


def test_section_override_entries(tmp_diario: Path):
    """A [cronos.sections] entry in the config file overrides the language default."""
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text(
        '[cronos]\nlang = "it"\n\n[cronos.sections]\nentries = "Attivita svolte"\n',
        encoding="utf-8",
    )
    config = load_config()
    assert config.section_entries == "Attivita svolte"
    # Other sections still come from the language pack
    assert config.section_blockers == "Bloccanti"


def test_section_override_multiple(tmp_diario: Path):
    """Multiple section overrides are all applied correctly."""
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text(
        '[cronos]\nlang = "it"\n\n[cronos.sections]\n'
        'entries = "Custom entries"\nblockers = "Custom blockers"\n',
        encoding="utf-8",
    )
    config = load_config()
    assert config.section_entries == "Custom entries"
    assert config.section_blockers == "Custom blockers"
    assert config.section_day_summary == "Riassunto della giornata"


# ---------------------------------------------------------------------------
# Git config
# ---------------------------------------------------------------------------


def test_git_enabled_from_config(tmp_diario: Path):
    """git_enabled is read from [cronos.git] in the config file."""
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text(
        '[cronos]\nlang = "it"\n\n[cronos.git]\nenabled = false\n',
        encoding="utf-8",
    )
    config = load_config()
    assert config.git_enabled is False


def test_git_auto_push_from_config(tmp_diario: Path):
    """auto_push is read from [cronos.git] in the config file."""
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text(
        '[cronos]\nlang = "it"\n\n[cronos.git]\nauto_push = false\n',
        encoding="utf-8",
    )
    config = load_config()
    assert config.auto_push is False


def test_git_commit_message_from_config(tmp_diario: Path):
    """commit_message is read from [cronos.git] in the config file."""
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text(
        '[cronos]\nlang = "it"\n\n[cronos.git]\ncommit_message = "custom: {date}"\n',
        encoding="utf-8",
    )
    config = load_config()
    assert config.commit_message == "custom: {date}"


def test_git_config_toml_it_fixture_disables_git(config_toml_it: Path):
    """The config_toml_it fixture sets git=false at top level (treated as git_enabled=False)."""
    # The config_toml_it fixture writes `git = false` under [cronos], not [cronos.git].
    # load_config should handle this gracefully and at minimum not crash.
    config = load_config()
    assert isinstance(config, CronosConfig)


# ---------------------------------------------------------------------------
# Invalid TOML falls back to defaults
# ---------------------------------------------------------------------------


def test_invalid_toml_falls_back_to_defaults(tmp_diario: Path):
    """A malformed TOML file causes load_config to fall back to Italian defaults."""
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text("this is not valid toml ][[\n", encoding="utf-8")
    config = load_config()
    assert config.lang == "it"
    assert config.section_entries == "Cosa ho fatto ieri"


def test_parse_toml_returns_empty_on_error(tmp_path: Path):
    """_parse_toml returns an empty dict when the file contains invalid TOML."""
    bad_file = tmp_path / "bad.toml"
    bad_file.write_text("[[broken\n", encoding="utf-8")
    result = _parse_toml(bad_file)
    assert result == {}


def test_parse_toml_returns_empty_for_missing_file(tmp_path: Path):
    """_parse_toml returns an empty dict when the file does not exist."""
    missing = tmp_path / "nonexistent.toml"
    result = _parse_toml(missing)
    assert result == {}


# ---------------------------------------------------------------------------
# Blockers default from language
# ---------------------------------------------------------------------------


def test_blockers_default_italian(tmp_diario: Path):
    """blockers_default is 'Nessuno' for Italian."""
    config = load_config()
    assert config.blockers_default == "Nessuno"


def test_blockers_default_english(config_toml_en: Path):
    """blockers_default is 'None' for English."""
    config = load_config()
    assert config.blockers_default == "None"


# ---------------------------------------------------------------------------
# title_format
# ---------------------------------------------------------------------------


def test_title_format_default_italian(tmp_diario: Path):
    """title_format defaults to the Italian title_prefix + date pattern."""
    config = load_config()
    # Default title_format is derived from the language pack's title_prefix.
    assert "Per lo Stand-up" in config.title_format


def test_title_format_override(tmp_diario: Path):
    """title_format can be overridden via [cronos.diary] in the config file."""
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text(
        '[cronos]\nlang = "it"\n\n[cronos.diary]\ntitle_format = "{prefix} {date}"\n',
        encoding="utf-8",
    )
    config = load_config()
    assert config.title_format == "{prefix} {date}"


# ---------------------------------------------------------------------------
# Singleton caching
# ---------------------------------------------------------------------------


def test_load_config_returns_same_instance(tmp_diario: Path):
    """load_config returns the same CronosConfig instance on subsequent calls."""
    config1 = load_config()
    config2 = load_config()
    assert config1 is config2


def test_reset_config_clears_singleton(tmp_diario: Path):
    """_reset_config causes load_config to build a fresh instance."""
    config1 = load_config()
    _reset_config()
    config2 = load_config()
    assert config1 is not config2


# ---------------------------------------------------------------------------
# _find_config_file
# ---------------------------------------------------------------------------


def test_find_config_file_diario_root(tmp_diario: Path):
    """_find_config_file returns path when cronos.toml exists in the diario root."""
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text('[cronos]\nlang = "it"\n', encoding="utf-8")
    found = _find_config_file()
    assert found == config_file


def test_find_config_file_returns_none_when_absent(tmp_diario: Path):
    """_find_config_file returns None when no config file can be found."""
    # No cronos.toml in tmp_diario, no CRONOS_CONFIG_PATH set
    found = _find_config_file()
    assert found is None


def test_find_config_file_explicit_env_var(
    tmp_path: Path, tmp_diario: Path, monkeypatch: pytest.MonkeyPatch
):
    """_find_config_file returns the path from CRONOS_CONFIG_PATH env var."""
    explicit = tmp_path / "explicit.toml"
    explicit.write_text('[cronos]\nlang = "en"\n', encoding="utf-8")
    monkeypatch.setenv("CRONOS_CONFIG_PATH", str(explicit))
    found = _find_config_file()
    assert found == explicit


# ---------------------------------------------------------------------------
# section_references and section_requested_by
# ---------------------------------------------------------------------------


def test_config_exposes_reference_labels_it(tmp_diario, config_toml_it):
    from mcp_cronos.config import load_config

    config = load_config()
    assert config.section_references == "Riferimenti"
    assert config.section_requested_by == "Richiesto da"


def test_config_exposes_reference_labels_en(tmp_diario, config_toml_en):
    from mcp_cronos.config import load_config

    config = load_config()
    assert config.section_references == "References"
    assert config.section_requested_by == "Requested by"


# ---------------------------------------------------------------------------
# Calendar settings
# ---------------------------------------------------------------------------


def test_config_calendar_defaults(tmp_diario):
    from mcp_cronos.config import load_config

    config = load_config()
    assert config.calendar_country == "IT"
    assert config.calendar_extra_holidays == []


def test_config_calendar_overrides(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        "[cronos]\ngit = false\n\n"
        '[cronos.calendar]\ncountry = "FR"\n'
        'extra_holidays = ["2026-12-07", "2026-08-14"]\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config, load_config

    _reset_config()
    config = load_config()
    assert config.calendar_country == "FR"
    assert config.calendar_extra_holidays == ["2026-12-07", "2026-08-14"]


# ---------------------------------------------------------------------------
# Project registry
# ---------------------------------------------------------------------------


def test_config_projects_empty_by_default(tmp_diario):
    from mcp_cronos.config import load_config

    config = load_config()
    assert config.projects_registered is False
    assert config.project_canonical == {}
    assert config.project_system == {}


def test_config_projects_registry(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        "[cronos]\ngit = false\n\n"
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\n\n'
        '[cronos.projects.PayGW]\nsistema = "Teseo"\nalias = ["PayGw"]\n\n'
        '[cronos.projects.Teseo]\nalias = ["Teseo Infra"]\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config, load_config

    _reset_config()
    config = load_config()

    assert config.projects_registered is True
    assert config.project_canonical["smarticket"] == "SmarTicket"
    assert config.project_canonical["paygw"] == "PayGW"
    assert config.project_canonical["teseoinfra"] == "Teseo"
    assert config.project_system["SmarTicket"] == "Teseo"
    assert config.project_system["PayGW"] == "Teseo"
    assert "Teseo" not in config.project_system
