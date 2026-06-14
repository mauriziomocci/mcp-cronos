"""
Shared pytest fixtures for the mcp-cronos test suite.

These fixtures provide isolated temporary environments for each test,
ensuring no test pollutes the real diary directory or global config state.
"""

from pathlib import Path

import pytest

from mcp_cronos.config import _reset_config


@pytest.fixture(autouse=True)
def _clean_config():
    """Reset the config singleton before and after every test."""
    _reset_config()
    yield
    _reset_config()


@pytest.fixture
def tmp_diario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Create a temporary diary directory and patch CRONOS_DIARIO_PATH to point to it.

    This is the base fixture for all tests that touch the filesystem. It ensures
    that no test accidentally writes to or reads from the user's real diary.

    Returns the path to the temporary diary root directory.
    """
    diario_dir = tmp_path / "diario"
    diario_dir.mkdir()
    monkeypatch.setenv("CRONOS_DIARIO_PATH", str(diario_dir))
    return diario_dir


@pytest.fixture
def sample_diary_it(tmp_diario: Path) -> Path:
    """
    Create a sample Italian diary file at 2026/04/2026-04-09.md with proper format.

    The file uses the standard diary structure with H1 title, entries section,
    H3 project entries, and blockers section.

    Returns the path to the created diary file.
    """
    month_dir = tmp_diario / "2026" / "04"
    month_dir.mkdir(parents=True, exist_ok=True)
    diary_file = month_dir / "2026-04-09.md"
    diary_file.write_text(
        "# Per lo Stand-up - 10 Aprile 2026\n\n"
        "## Cosa ho fatto ieri\n\n"
        "### MCP Cronos - Refactoring config system\n\n"
        "Migrated all hardcoded strings to config.\n\n"
        "---\n\n"
        "### SmarTicket - Fix login bug\n\n"
        "*-Richiesto da Marco-*\n\n"
        "Fixed authentication timeout.\n\n"
        "**Riferimenti:**\n"
        "- Repository: smarticket-backend\n"
        "- Branch: `fix/login-timeout`\n\n"
        "---\n\n"
        "## Bloccanti\n\n"
        "Nessuno\n",
        encoding="utf-8",
    )
    return diary_file


@pytest.fixture
def sample_diary_en(tmp_diario: Path) -> Path:
    """
    Create a sample English diary file at 2026/04/2026-04-09.md with proper format.

    Returns the path to the created diary file.
    """
    month_dir = tmp_diario / "2026" / "04"
    month_dir.mkdir(parents=True, exist_ok=True)
    diary_file = month_dir / "2026-04-09.md"
    diary_file.write_text(
        "# For Stand-up - April 10, 2026\n\n"
        "## What I did yesterday\n\n"
        "### MCP Cronos - Config refactoring\n\n"
        "Migrated all hardcoded strings to config.\n\n"
        "---\n\n"
        "## Blockers\n\n"
        "None\n",
        encoding="utf-8",
    )
    return diary_file


@pytest.fixture
def config_toml_it(tmp_diario: Path) -> Path:
    """
    Create a cronos.toml config file with lang='it' and git disabled inside tmp_diario.

    Returns the path to the created config file.
    """
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text(
        '[cronos]\nlang = "it"\ngit = false\n',
        encoding="utf-8",
    )
    return config_file


@pytest.fixture
def config_toml_en(tmp_diario: Path) -> Path:
    """
    Create a cronos.toml config file with lang='en' and git disabled inside tmp_diario.

    Returns the path to the created config file.
    """
    config_file = tmp_diario / "cronos.toml"
    config_file.write_text(
        '[cronos]\nlang = "en"\ngit = false\n',
        encoding="utf-8",
    )
    return config_file
