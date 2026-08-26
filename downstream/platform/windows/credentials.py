"""Credential-safe child environment projection for native services."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping

_BASE_KEYS = frozenset({
    "APPDATA",
    "COMSPEC",
    "HERMES_HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "LANG",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "PROGRAMDATA",
    "PYTHONUTF8",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERPROFILE",
})
_SECRET_NAME = re.compile(
    r"(?:API[_-]?KEY|CREDENTIAL|PASSWORD|SECRET|TOKEN)", re.IGNORECASE
)


def safe_child_environment(
    source: Mapping[str, str] | None = None,
    *,
    overrides: Mapping[str, str] | None = None,
    allowed_secret_names: frozenset[str] = frozenset(),
) -> dict[str, str]:
    """Project an explicit environment without ambient credential inheritance."""
    source = os.environ if source is None else source
    allowed = {key.casefold() for key in _BASE_KEYS | allowed_secret_names}
    result = {key: value for key, value in source.items() if key.casefold() in allowed}
    for key, value in (overrides or {}).items():
        if _SECRET_NAME.search(key) and key not in allowed_secret_names:
            raise ValueError(
                f"Secret-like child environment key requires explicit allowlisting: {key}"
            )
        result[key] = value
    return result


__all__ = ["safe_child_environment"]
