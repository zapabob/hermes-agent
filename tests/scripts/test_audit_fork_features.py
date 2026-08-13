import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MERGE_TOOLS = REPO_ROOT / "scripts" / "merge_tools"
if str(MERGE_TOOLS) not in sys.path:
    sys.path.insert(0, str(MERGE_TOOLS))

import audit_fork_features as audit


def test_current_text_prefers_worktree_file(monkeypatch, tmp_path):
    target = tmp_path / "hermes_cli" / "config_defaults.py"
    target.parent.mkdir(parents=True)
    target.write_text("working tree\n", encoding="utf-8")
    monkeypatch.setattr(audit, "REPO_ROOT", tmp_path)

    assert audit.current_text("hermes_cli/config_defaults.py") == "working tree\n"


def test_expected_overlay_differences_are_informational(monkeypatch, tmp_path):
    strategy = tmp_path / "strategy.json"
    strategy.write_text(
        json.dumps(
            {
                "rules": [
                    {"pattern": "feature.py", "action": "official_with_overlay"}
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "feature.py").write_text("current\n", encoding="utf-8")

    monkeypatch.setattr(audit, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(audit, "STRATEGY", strategy)
    monkeypatch.setattr(audit, "SYMBOL_CHECKS", {})
    monkeypatch.setattr(audit, "fork_files", lambda: ["feature.py"])
    monkeypatch.setattr(audit, "git_show", lambda ref, path: "baseline\n")

    assert audit.main() == 0


def test_missing_preserved_file_fails_audit(monkeypatch, tmp_path):
    strategy = tmp_path / "strategy.json"
    strategy.write_text(
        json.dumps(
            {"rules": [{"pattern": "missing.py", "action": "preserve_custom"}]}
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(audit, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(audit, "STRATEGY", strategy)
    monkeypatch.setattr(audit, "SYMBOL_CHECKS", {})
    monkeypatch.setattr(audit, "fork_files", lambda: ["missing.py"])
    monkeypatch.setattr(audit, "git_show", lambda ref, path: "baseline\n")

    assert audit.main() == 1


def test_intentionally_missing_file_does_not_fail_audit(monkeypatch, tmp_path):
    strategy = tmp_path / "strategy.json"
    strategy.write_text(
        json.dumps(
            {
                "rules": [{"pattern": "retired.md", "action": "preserve_custom"}],
                "audit_ignore_missing": ["retired.md"],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(audit, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(audit, "STRATEGY", strategy)
    monkeypatch.setattr(audit, "SYMBOL_CHECKS", {})
    monkeypatch.setattr(audit, "fork_files", lambda: ["retired.md"])
    monkeypatch.setattr(audit, "git_show", lambda ref, path: "baseline\n")

    assert audit.main() == 0
