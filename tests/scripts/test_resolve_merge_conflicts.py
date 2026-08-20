"""Safety contracts for scripts/merge_tools/resolve_merge_conflicts.py."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MERGE_TOOLS = REPO_ROOT / "scripts" / "merge_tools"
if str(MERGE_TOOLS) not in sys.path:
    sys.path.insert(0, str(MERGE_TOOLS))

import resolve_merge_conflicts as resolver_module  # noqa: E402
from upstream_merge_policy import Classification  # noqa: E402


def _classification(action: str) -> Classification:
    return Classification(
        path="api.py",
        action=action,
        note="test classification",
        pattern="api.py",
        touched_upstream=True,
        touched_custom=True,
    )


def _resolver(*, dry_run: bool) -> resolver_module.Resolver:
    return resolver_module.Resolver(
        upstream_ref="upstream/main",
        dry_run=dry_run,
        old_head="old-head",
        merge_base="merge-base",
    )


def test_manual_followup_dry_run_requires_approval(monkeypatch):
    monkeypatch.setattr(resolver_module, "unresolved_files", lambda: [])
    classification = _classification("manual_api_followup")
    resolver = _resolver(dry_run=True)

    result = resolver.apply_action(classification.path, classification.action)
    resolver.record(classification, result)
    blocked, unresolved = resolver_module.summarize_results(
        [classification],
        resolver,
        blocker_actions=frozenset({"official_with_overlay", "manual_api_followup"}),
    )

    assert result == "manual_approval_required"
    assert blocked == ["api.py"]
    assert unresolved == []


def test_official_overlay_dry_run_is_planned_not_blocked(monkeypatch):
    monkeypatch.setattr(resolver_module, "unresolved_files", lambda: [])
    classification = _classification("official_with_overlay")
    resolver = _resolver(dry_run=True)

    result = resolver.apply_action(classification.path, classification.action)
    resolver.record(classification, result)
    blocked, _ = resolver_module.summarize_results(
        [classification],
        resolver,
        blocker_actions=frozenset({"official_with_overlay", "manual_api_followup"}),
    )

    assert result == "overlay_planned"
    assert blocked == []


def test_manual_followup_apply_preserves_existing_overlay_behavior(monkeypatch):
    monkeypatch.setattr(resolver_module, "unresolved_files", lambda: [])
    monkeypatch.setattr(resolver_module, "merge_file_overlay", lambda *args, **kwargs: True)
    classification = _classification("manual_api_followup")
    resolver = _resolver(dry_run=False)

    result = resolver.apply_action(classification.path, classification.action)
    resolver.record(classification, result)
    blocked, _ = resolver_module.summarize_results(
        [classification],
        resolver,
        blocker_actions=frozenset({"official_with_overlay", "manual_api_followup"}),
    )

    assert result == "overlay_applied"
    assert blocked == []
