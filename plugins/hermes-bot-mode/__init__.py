"""Hermes Bot Mode integration.

The feature UI is kept in the ``desktop`` git submodule and is loaded by
Hermes Desktop's runtime plugin loader.  The Python half is intentionally a
no-op: keeping a valid ``register(ctx)`` entrypoint makes the package visible
to Hermes' plugin inventory without duplicating desktop behavior in the
agent core.
"""

from __future__ import annotations

from pathlib import Path

PLUGIN_NAME = "hermes-bot-mode"


def submodule_root() -> Path:
    """Return the checked-out Hermes-Bot-Mode submodule root."""
    return Path(__file__).resolve().parent / "desktop"


def submodule_ready() -> bool:
    """Return whether the desktop plugin entrypoint is checked out."""
    return (submodule_root() / "plugin.js").is_file()


def register(ctx) -> None:
    """Register the desktop-only integration with Hermes.

    Desktop discovers ``desktop/plugin.js`` independently.  There are no
    agent-callable tools to register here, but this entrypoint is required by
    Hermes' Python plugin discovery contract.
    """
    return None
