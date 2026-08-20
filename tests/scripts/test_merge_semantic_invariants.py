"""Hermetic contracts for upstream overlay semantic guards."""

from __future__ import annotations

import sys
import types
from pathlib import Path


MERGE_TOOLS = Path(__file__).resolve().parents[2] / "scripts" / "merge_tools"
if str(MERGE_TOOLS) not in sys.path:
    sys.path.insert(0, str(MERGE_TOOLS))

import merge_semantic_invariants as invariants  # noqa: E402
import resolve_merge_conflicts as resolver_module  # noqa: E402


GOOD_REGISTRY = """
CommandDef("worktree", "worktree"),
CommandDef("suggestions", "suggestions", aliases=("suggest",), args_hint="")
CommandDef("blueprint", "blueprint", aliases=("bp",), args_hint="")
CommandDef("auth", "auth"),
"""


def test_command_registry_requires_official_and_fork_commands_and_aliases():
    assert invariants.validate_command_registry(GOOD_REGISTRY) == []
    errors = invariants.validate_command_registry(GOOD_REGISTRY.replace('aliases=("bp",)', ''))
    assert "CommandDef('blueprint') missing alias 'bp'" in errors


def test_canonical_cli_names_require_fork_and_official_entries():
    assert invariants.validate_cli_command_names('"harness", "peer", "worktree"') == []
    assert "BUILTIN_SUBCOMMANDS missing 'worktree'" in invariants.validate_cli_command_names('"harness", "peer"')


def test_dry_run_semantically_previews_manual_command_overlay(monkeypatch):
    fake_overlay = types.SimpleNamespace(
        three_way_merge=lambda *args, **kwargs: (0, GOOD_REGISTRY),
    )
    monkeypatch.setitem(sys.modules, "apply_three_way_overlay", fake_overlay)
    resolver = resolver_module.Resolver(
        upstream_ref="upstream/main",
        dry_run=True,
        old_head="old-head",
        merge_base="merge-base",
        semantic_invariants={"hermes_cli/commands.py": "command_registry"},
    )

    result = resolver.apply_action("hermes_cli/commands.py", "manual_api_followup")

    assert result == "manual_approval_required_preview_valid"
