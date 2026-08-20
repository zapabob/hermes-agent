"""Small, source-text invariants for high-risk upstream overlay paths.

These checks deliberately avoid importing the application.  They are used by
the merge driver before and after an overlay, when the checkout may contain a
partially merged tree or dependencies may not be installed yet.
"""

from __future__ import annotations

import re
from pathlib import Path


REQUIRED_COMMANDS = {
    "worktree": ("worktree",),
    "suggestions": ("suggestions", "suggest"),
    "blueprint": ("blueprint", "bp"),
    "auth": ("auth",),
}


def _command_span(text: str, name: str) -> str | None:
    match = re.search(
        rf"CommandDef\(\s*['\"]{re.escape(name)}['\"](?P<body>.*?)\s*\),",
        text,
        re.DOTALL,
    )
    return match.group(0) if match else None


def validate_command_registry(text: str) -> list[str]:
    """Return missing command/alias diagnostics for ``hermes_cli/commands.py``."""
    errors: list[str] = []
    for command, aliases in REQUIRED_COMMANDS.items():
        span = _command_span(text, command)
        if span is None:
            errors.append(f"missing CommandDef({command!r})")
            continue
        for alias in aliases[1:]:
            if not re.search(rf"aliases\s*=\s*\([^)]*['\"]{re.escape(alias)}['\"]", span):
                errors.append(f"CommandDef({command!r}) missing alias {alias!r}")
    return errors


def validate_cli_command_names(text: str) -> list[str]:
    """Return missing canonical top-level CLI names."""
    return [
        f"BUILTIN_SUBCOMMANDS missing {name!r}"
        for name in ("harness", "peer", "worktree")
        if not re.search(rf"['\"]{name}['\"]", text)
    ]


def validate_repo(repo_root: Path) -> list[str]:
    """Validate the command registry and canonical CLI collision boundary."""
    errors: list[str] = []
    commands_path = repo_root / "hermes_cli" / "commands.py"
    names_path = repo_root / "hermes_cli" / "cli_command_names.py"
    if not commands_path.is_file():
        errors.append(f"missing {commands_path.relative_to(repo_root).as_posix()}")
    else:
        errors.extend(validate_command_registry(commands_path.read_text(encoding="utf-8")))
    if not names_path.is_file():
        errors.append(f"missing {names_path.relative_to(repo_root).as_posix()}")
    else:
        errors.extend(validate_cli_command_names(names_path.read_text(encoding="utf-8")))
    return errors
