"""Guard against mixed-checkout ImportError for resolve_fallback_chain."""

from __future__ import annotations

import hermes_cli.fallback_config as fb


def test_fallback_config_exports_resolve_and_get():
    """Desktop/gateway crash when resolve_fallback_chain is missing from the tree."""
    assert callable(getattr(fb, "get_fallback_chain", None))
    assert callable(getattr(fb, "resolve_fallback_chain", None))


def test_resolve_fallback_chain_import_shim_survives_missing_symbol(monkeypatch):
    """Callers must degrade to get_fallback_chain instead of crashing at import."""
    monkeypatch.delattr(fb, "resolve_fallback_chain", raising=False)

    try:
        from hermes_cli.fallback_config import resolve_fallback_chain as resolved
    except ImportError:
        from hermes_cli.fallback_config import get_fallback_chain as resolved

    assert resolved is fb.get_fallback_chain
