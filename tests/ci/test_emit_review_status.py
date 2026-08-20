"""Tests for scripts/ci/emit_review_status.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "emit_review_status.py"
_spec = importlib.util.spec_from_file_location("emit_review_status", _PATH)
if _spec is None or _spec.loader is None:
    raise ImportError("Failed to load emit_review_status.py")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["emit_review_status"] = _mod
_spec.loader.exec_module(_mod)


def test_ci_review_status_links_to_each_sensitive_file_change():
    results = _mod.build_results(
        ci_review=True,
        mcp_catalog=False,
        supply_chain=False,
        label_present=False,
        ci_review_files='[".github/workflows/ci.yaml", "apps/desktop/eslint.config.mjs"]',
        repo_url="https://github.com/nousresearch/hermes-agent",
        base_sha="base456",
        head_sha="abc123",
    )

    assert results[0]["detail"] == (
        "**Sensitive files changed:**\n"
        "- [`.github/workflows/ci.yaml`](https://github.com/nousresearch/hermes-agent/compare/base456...abc123#diff-944291df2c9c06359d37cc8833d182d705c9e8c3108e7cfe132d61a06e9133dd)\n"
        "- [`apps/desktop/eslint.config.mjs`](https://github.com/nousresearch/hermes-agent/compare/base456...abc123#diff-a45471520795db6e46840d1ba2a82c1f8a2841039bd60fb50624488c5f192438)"
    )


def test_approved_ci_review_is_visible_info():
    results = _mod.build_results(
        ci_review=True,
        mcp_catalog=False,
        supply_chain=False,
        label_present=True,
        ci_review_files='[".github/workflows/ci.yaml"]',
        repo_url="https://github.com/nousresearch/hermes-agent",
        base_sha="base456",
        head_sha="abc123",
    )

    assert results == [{
        "kind": "info",
        "title": "CI-sensitive file review",
        "summary": (
            "PR touches sensitive files, but the `ci-reviewed` label has been "
            "added, approving them."
        ),
        "detail": (
            "**Sensitive files changed:**\n"
            "- [`.github/workflows/ci.yaml`](https://github.com/nousresearch/hermes-agent/compare/base456...abc123#diff-944291df2c9c06359d37cc8833d182d705c9e8c3108e7cfe132d61a06e9133dd)"
        ),
    }]
