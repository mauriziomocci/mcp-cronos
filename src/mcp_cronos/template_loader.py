"""
Template loader for LLM instruction templates.

Provides a single entry point, load_template(), that resolves a named template
with a two-level priority scheme:

1. User override: {CRONOS_DIARIO_PATH}/templates/{name}.md
2. Built-in default: src/mcp_cronos/default_templates/{name}.md

This allows users to customise the LLM prompts without touching the package
source, while keeping sensible defaults bundled with the distribution.
"""

import os
from pathlib import Path

_BUILTIN_DIR = Path(__file__).parent / "default_templates"

# Authoritative set of valid template names. Guards against typos and prevents
# accidental traversal to arbitrary files outside the templates directory.
_VALID_TEMPLATES = {"fine_giornata", "standup", "consolida"}


def load_template(name: str) -> str:
    """
    Load a named LLM instruction template, with optional user override.

    Resolution order:
    1. {CRONOS_DIARIO_PATH}/templates/{name}.md  (user override, if present)
    2. default_templates/{name}.md               (bundled built-in)

    Args:
        name: Template name — must be one of "fine_giornata", "standup", "consolida".

    Returns:
        The full text content of the resolved template file.

    Raises:
        FileNotFoundError: If name is not a recognised template identifier.
    """
    if name not in _VALID_TEMPLATES:
        raise FileNotFoundError(
            f"Unknown template '{name}'. Valid templates: {sorted(_VALID_TEMPLATES)}"
        )

    # Check for user-provided override before falling back to the built-in.
    diario_path = os.environ.get("CRONOS_DIARIO_PATH")
    if diario_path:
        user_override = Path(diario_path) / "templates" / f"{name}.md"
        if user_override.exists():
            return user_override.read_text(encoding="utf-8")

    builtin = _BUILTIN_DIR / f"{name}.md"
    return builtin.read_text(encoding="utf-8")
