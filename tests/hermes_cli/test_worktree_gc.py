"""Behavior contracts for hermes_cli.worktree_gc (attended reclaim).

Each guard gets its own contract against a REAL git repo fixture (no mocks —
the entire value of these tests is exercising actual git verdicts):

- clean + fully merged tree        → reap
- untracked-only dirt              → reap-archive (files archived, then removed)
- tracked modifications            → keep, any age
- unique unpushed commits          → keep
- patch-equivalent commits (rebase/squash-merge leak) → reap
- live-locked tree                 → keep
- kanban t_<hex> tree              → keep (owned by kanban gc)
- branch GC: merged branch deleted, unique-commit branch kept,
  checked-out branch kept, protected names kept
- reclaim operates ONLY on the frozen audit list (concurrent-session trap)
"""

import os
import json
import subprocess
from pathlib import Path

import pytest

from hermes_cli import worktree_gc


def _git(args, cwd, env=None):
    e = dict(os.environ)
    e.update({
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    })
    if env:
        e.update(env)
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=str(cwd), env=e,
    )
    assert result.returncode == 0, f"git {args} failed: {result.stderr}"
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """origin (bare) + clone with .worktrees/, HOME redirected for archives."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()

    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(["init", "--bare", "-b", "main"], origin)

    clone = tmp_path / "repo"
    _git(["clone", str(origin), str(clone)], tmp_path)
    (clone / "README.md").write_text("hello\n")
    _git(["add", "."], clone)
    _git(["commit", "-m", "init"], clone)
    _git(["push", "origin", "main"], clone)
    # origin/HEAD so upstream resolution works like a real clone.
    _git(["remote", "set-head", "origin", "main"], clone)
    (clone / ".worktrees").mkdir()
    return clone


def _add_worktree(repo_path, name, branch=None):
    tree = repo_path / ".worktrees" / name
    branch = branch or f"hermes/{name}"
    _git(["worktree", "add", str(tree), "-b", branch], repo_path)
    return tree, branch


def _verdict(records, name):
    match = [record for record in records if record.name == name]
    assert match, f"no record for {name}"
    return match[0]


class TestAuditVerdicts:
    def test_clean_merged_tree_reaps(self, repo):
        _add_worktree(repo, "hermes-clean")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        assert _verdict(records, "hermes-clean").verdict == "reap"

    def test_tracked_modifications_keep(self, repo):
        tree, _ = _add_worktree(repo, "hermes-dirty")
        (tree / "README.md").write_text("edited\n")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        record = _verdict(records, "hermes-dirty")
        assert record.verdict == "keep"
        assert "tracked" in record.reason

    def test_untracked_only_is_reap_archive(self, repo):
        tree, _ = _add_worktree(repo, "hermes-scratch")
        (tree / "PR_BODY_DRAFT.md").write_text("draft\n")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        record = _verdict(records, "hermes-scratch")
        assert record.verdict == "reap-archive"
        assert record.untracked == ["PR_BODY_DRAFT.md"]

    def test_unique_unpushed_commits_keep(self, repo):
        tree, _ = _add_worktree(repo, "hermes-work")
        (tree / "new.py").write_text("x = 1\n")
        _git(["add", "."], tree)
        _git(["commit", "-m", "unique work"], tree)
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        record = _verdict(records, "hermes-work")
        assert record.verdict == "keep"
        assert "unpushed" in record.reason

    def test_patch_equivalent_commits_reap(self, repo):
        """The squash/rebase-merge leak: local commit unreachable from any
        remote ref but patch-equivalent to an upstream commit → merged work."""
        tree, _ = _add_worktree(repo, "hermes-merged")
        (tree / "feat.py").write_text("y = 2\n")
        _git(["add", "."], tree)
        _git(["commit", "-m", "feat"], tree)
        sha = _git(["rev-parse", "HEAD"], tree)
        # "Merge" it to main with a DIFFERENT committer so the cherry-pick
        # produces a distinct sha (same-second identical-committer cherry
        # picks can produce the identical sha — pitfall from the skill).
        _git(["cherry-pick", sha], repo,
             env={"GIT_COMMITTER_NAME": "other", "GIT_COMMITTER_EMAIL": "o@o"})
        _git(["push", "origin", "main"], repo)
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        assert _verdict(records, "hermes-merged").verdict == "reap"

    def test_live_locked_tree_keeps(self, repo):
        tree, _ = _add_worktree(repo, "hermes-live")
        _git(["worktree", "lock", str(tree),
              "--reason", f"hermes pid={os.getpid()}"], repo)
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        record = _verdict(records, "hermes-live")
        assert record.verdict == "keep"
        assert "in use" in record.reason

    def test_kanban_tree_untouched(self, repo):
        _add_worktree(repo, "t_deadbeef", branch="kanban/t_deadbeef")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        record = _verdict(records, "t_deadbeef")
        assert record.verdict == "keep"
        assert "kanban" in record.reason

    def test_shallow_audit_and_dry_run_are_strictly_read_only(
        self, repo, monkeypatch,
    ):
        import cli

        tree, _ = _add_worktree(repo, "hermes-shallow")
        (tree / "local.py").write_text("local = True\n")
        _git(["add", "local.py"], tree)
        _git(["commit", "-m", "local shallow work"], tree)

        monkeypatch.setattr(cli, "_repo_is_shallow", lambda _root: True)

        def forbidden(*_args, **_kwargs):
            pytest.fail("read-only audit/dry-run must not fetch or write cache")

        monkeypatch.setattr(cli, "_deepen_shallow_repo", forbidden)
        monkeypatch.setattr(cli, "_save_worktree_merge_cache", forbidden)

        tree_records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        tree_record = _verdict(tree_records, "hermes-shallow")
        assert tree_record.verdict == "keep"
        assert "shallow history" in tree_record.reason
        branch_records = worktree_gc.audit_branches(str(repo))
        assert branch_records
        assert all(record.verdict == "keep" for record in branch_records)

        actions = worktree_gc.reclaim_worktrees(
            str(repo), dry_run=True, records=tree_records,
        )
        actions += worktree_gc.reclaim_branches(
            str(repo), dry_run=True, records=branch_records,
        )
        assert actions == []
        assert tree.exists()


class TestReclaim:
    def test_reap_removes_tree_and_branch(self, repo):
        tree, branch = _add_worktree(repo, "hermes-clean")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        actions = worktree_gc.reclaim_worktrees(str(repo), records=records)
        assert any("removed hermes-clean" in a for a in actions)
        assert not tree.exists()
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", branch],
            capture_output=True, text=True, cwd=str(repo),
        )
        assert probe.returncode != 0, "branch should be gone with its tree"

    def test_untracked_files_archived_before_removal(self, repo):
        tree, _ = _add_worktree(repo, "hermes-scratch")
        (tree / "NOTES.md").write_text("important scribbles\n")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        worktree_gc.reclaim_worktrees(str(repo), records=records)
        assert not tree.exists()
        archive_root = Path.home() / ".hermes" / "archive" / "worktree-prune"
        archived = list(archive_root.rglob("NOTES.md"))
        assert archived, "untracked file must be archived, not destroyed"
        assert archived[0].read_text() == "important scribbles\n"

    def test_archive_second_move_failure_rolls_back_first(self, repo, monkeypatch):
        tree, _ = _add_worktree(repo, "hermes-archive-rollback")
        first = tree / "FIRST.md"
        second = tree / "SECOND.md"
        first.write_text("first remains recoverable\n")
        second.write_text("second remains recoverable\n")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        real_move = worktree_gc.shutil.move
        move_count = 0

        def fail_second_move(src, dst, *args, **kwargs):
            nonlocal move_count
            move_count += 1
            if move_count == 2:
                raise OSError("injected second archive move failure")
            return real_move(src, dst, *args, **kwargs)

        monkeypatch.setattr(worktree_gc.shutil, "move", fail_second_move)
        actions = worktree_gc.reclaim_worktrees(str(repo), records=records)

        assert tree.exists()
        assert first.read_text() == "first remains recoverable\n"
        assert second.read_text() == "second remains recoverable\n"
        assert any("archive of untracked files failed" in action
                   for action in actions)
        archive_root = Path.home() / ".hermes" / "archive" / "worktree-prune"
        assert not list(archive_root.rglob("FIRST.md"))

    def test_dry_run_changes_nothing(self, repo):
        tree, _ = _add_worktree(repo, "hermes-clean")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        actions = worktree_gc.reclaim_worktrees(
            str(repo), dry_run=True, records=records
        )
        assert any("would remove" in a for a in actions)
        assert tree.exists()

    def test_frozen_list_ignores_trees_created_after_audit(self, repo):
        """Concurrent-session trap: a tree created between audit and reclaim
        must be out of scope by construction."""
        _add_worktree(repo, "hermes-old")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        late_tree, _ = _add_worktree(repo, "hermes-late")
        worktree_gc.reclaim_worktrees(str(repo), records=records)
        assert late_tree.exists(), "tree created after the audit must survive"

    def test_dead_locked_tree_is_unlocked_and_reaped(self, repo):
        tree, _ = _add_worktree(repo, "hermes-zombie")
        _git(["worktree", "lock", str(tree),
              "--reason", "hermes pid=999999999"], repo)
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        assert _verdict(records, "hermes-zombie").verdict == "reap"
        worktree_gc.reclaim_worktrees(str(repo), records=records)
        assert not tree.exists()

    def test_tracked_edit_after_audit_is_kept(self, repo):
        tree, _ = _add_worktree(repo, "hermes-raced-edit")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        (tree / "README.md").write_text("work started after audit\n")

        actions = worktree_gc.reclaim_worktrees(str(repo), records=records)

        assert tree.exists()
        assert any("tracked changes appeared" in action for action in actions)

    def test_live_lock_acquired_after_audit_is_kept(self, repo):
        tree, _ = _add_worktree(repo, "hermes-raced-lock")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        _git(["worktree", "lock", str(tree),
              "--reason", f"hermes pid={os.getpid()}"], repo)

        actions = worktree_gc.reclaim_worktrees(str(repo), records=records)

        assert tree.exists()
        assert any("live-locked" in action for action in actions)

    def test_unique_commit_after_audit_is_kept(self, repo):
        tree, branch = _add_worktree(repo, "hermes-raced-commit")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        (tree / "new.py").write_text("valuable = True\n")
        _git(["add", "new.py"], tree)
        _git(["commit", "-m", "new work after audit"], tree)

        actions = worktree_gc.reclaim_worktrees(str(repo), records=records)

        assert tree.exists()
        assert _git(["rev-parse", "--verify", branch], repo)
        assert any("HEAD or branch changed" in action for action in actions)

    def test_edit_after_final_revalidation_is_caught_by_git_remove(
        self, repo, monkeypatch,
    ):
        import cli

        tree, _ = _add_worktree(repo, "hermes-last-moment-edit")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        # Keep the contract focused on the final real-Git dirty guard; busy CI
        # hosts can otherwise make the repeated five-second ancillary probes
        # fail closed before the remove call is reached.
        monkeypatch.setattr(cli, "_worktree_lock_is_live",
                            lambda *_args, **_kwargs: "absent")
        monkeypatch.setattr(cli, "_worktree_has_unpushed_commits",
                            lambda *_args, **_kwargs: False)
        real_git = worktree_gc._git
        injected = False

        def edit_before_remove(args, cwd, timeout=15):
            nonlocal injected
            if args[:2] == ["worktree", "remove"] and not injected:
                injected = True
                (tree / "README.md").write_text("last moment real work\n")
            return real_git(args, cwd, timeout)

        monkeypatch.setattr(worktree_gc, "_git", edit_before_remove)
        actions = worktree_gc.reclaim_worktrees(str(repo), records=records)

        assert tree.exists()
        assert (tree / "README.md").read_text() == "last moment real work\n"
        assert any("failed to remove hermes-last-moment-edit" in action
                   for action in actions)

    def test_stale_merged_pr_with_reused_branch_name_is_kept(
        self, repo, monkeypatch,
    ):
        tree, branch = _add_worktree(repo, "hermes-reused-pr")
        _git(["push", "-u", "origin", branch], tree)
        old_tip = _git(["rev-parse", "HEAD"], tree)
        (tree / "new.py").write_text("new incarnation\n")
        _git(["add", "new.py"], tree)
        _git(["commit", "-m", "new branch incarnation"], tree)

        def stale_pr(*_args, **_kwargs):
            return subprocess.CompletedProcess(
                args=["gh"], returncode=0,
                stdout=json.dumps([{"headRefOid": old_tip}]), stderr="",
            )

        monkeypatch.setattr(worktree_gc, "_gh", stale_pr)
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)

        record = _verdict(records, "hermes-reused-pr")
        assert record.verdict == "keep"
        assert "unpushed" in record.reason
        assert tree.exists()

    def test_unpublished_branch_name_is_not_disclosed_to_github(
        self, repo, monkeypatch,
    ):
        tree, _ = _add_worktree(repo, "private-local-name")
        (tree / "private.py").write_text("private = True\n")
        _git(["add", "private.py"], tree)
        _git(["commit", "-m", "private local work"], tree)

        def forbidden(*_args, **_kwargs):
            pytest.fail("an unpublished local branch name must not reach gh")

        monkeypatch.setattr(worktree_gc, "_gh", forbidden)
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)

        assert _verdict(records, "private-local-name").verdict == "keep"

    def test_shallow_deepen_preserves_frozen_tree_scope(
        self, repo, monkeypatch,
    ):
        import cli

        old_tree, _ = _add_worktree(repo, "hermes-approved")
        records = worktree_gc.audit_worktrees(str(repo), with_sizes=False)
        shallow = True
        late_tree = None

        def is_shallow(_root):
            return shallow

        def deepen(_root):
            nonlocal shallow, late_tree
            shallow = False
            late_tree, _ = _add_worktree(repo, "hermes-late-after-audit")

        monkeypatch.setattr(cli, "_repo_is_shallow", is_shallow)
        monkeypatch.setattr(cli, "_deepen_shallow_repo", deepen)

        actions = worktree_gc.reclaim_worktrees(str(repo), records=records)

        assert not old_tree.exists()
        assert late_tree is not None and late_tree.exists()
        assert all("hermes-late-after-audit" not in action for action in actions)


class TestBranchGC:
    def test_merged_branch_deleted_any_name(self, repo):
        """Branch GC is content-gated, not name-gated: any fully-merged local
        branch is safe to delete regardless of prefix."""
        _git(["branch", "salv-12345", "main"], repo)
        _git(["branch", "feat/some-old-thing", "main"], repo)
        records = worktree_gc.audit_branches(str(repo))
        by_name = {record.name: record for record in records}
        assert by_name["salv-12345"].verdict == "delete"
        assert by_name["feat/some-old-thing"].verdict == "delete"
        worktree_gc.reclaim_branches(str(repo), records=records)
        out = _git(["branch", "--format=%(refname:short)"], repo)
        assert "salv-12345" not in out
        assert "feat/some-old-thing" not in out

    def test_unique_commit_branch_kept(self, repo):
        _git(["checkout", "-b", "feat/real-work"], repo)
        (repo / "wip.py").write_text("z = 3\n")
        _git(["add", "."], repo)
        _git(["commit", "-m", "wip"], repo)
        _git(["checkout", "main"], repo)
        records = worktree_gc.audit_branches(str(repo))
        by_name = {record.name: record for record in records}
        assert by_name["feat/real-work"].verdict == "keep"
        assert "unique" in by_name["feat/real-work"].reason

    def test_rev_list_failure_fails_closed(self, repo, monkeypatch):
        branch = "feat/rev-list-failure"
        _git(["checkout", "-b", branch], repo)
        (repo / "work.py").write_text("valuable = True\n")
        _git(["add", "work.py"], repo)
        _git(["commit", "-m", "valuable work"], repo)
        _git(["checkout", "main"], repo)

        real_git = worktree_gc._git

        def fail_rev_list(args, cwd, timeout=15):
            if args[:2] == ["rev-list", "--count"] and args[-1].endswith(branch):
                return subprocess.CompletedProcess(
                    args=["git", *args], returncode=1, stdout="", stderr="failed",
                )
            return real_git(args, cwd, timeout)

        monkeypatch.setattr(worktree_gc, "_git", fail_rev_list)
        records = worktree_gc.audit_branches(str(repo))
        record = next(item for item in records if item.name == branch)

        assert record.verdict == "keep"
        assert "rev-list failed" in record.reason

    def test_patch_equivalent_branch_deleted(self, repo):
        """Rebase-merged PR branch: SHAs differ from main but every commit is
        patch-equivalent — the dominant branch leak."""
        _git(["checkout", "-b", "fix/landed"], repo)
        (repo / "fix.py").write_text("a = 4\n")
        _git(["add", "."], repo)
        _git(["commit", "-m", "fix"], repo)
        sha = _git(["rev-parse", "HEAD"], repo)
        _git(["checkout", "main"], repo)
        _git(["cherry-pick", sha], repo,
             env={"GIT_COMMITTER_NAME": "other", "GIT_COMMITTER_EMAIL": "o@o"})
        _git(["push", "origin", "main"], repo)
        records = worktree_gc.audit_branches(str(repo))
        by_name = {record.name: record for record in records}
        assert by_name["fix/landed"].verdict == "delete"
        assert "patch-equivalent" in by_name["fix/landed"].reason

    def test_checked_out_and_protected_kept(self, repo):
        _tree, branch = _add_worktree(repo, "hermes-active")
        records = worktree_gc.audit_branches(str(repo))
        by_name = {record.name: record for record in records}
        assert by_name["main"].verdict == "keep"
        assert by_name[branch].verdict == "keep"

    def test_branch_tip_move_after_audit_is_kept(self, repo):
        branch = "feat/raced-tip"
        _git(["branch", branch, "main"], repo)
        records = worktree_gc.audit_branches(str(repo))
        record = next(item for item in records if item.name == branch)
        assert record.verdict == "delete"

        _git(["checkout", branch], repo)
        (repo / "valuable.py").write_text("do_not_delete = True\n")
        _git(["add", "valuable.py"], repo)
        _git(["commit", "-m", "branch moved after audit"], repo)
        _git(["checkout", "main"], repo)

        actions = worktree_gc.reclaim_branches(str(repo), records=[record])

        assert _git(["rev-parse", "--verify", branch], repo)
        assert any("tip changed" in action for action in actions)

    def test_atomic_delete_refuses_tip_move_after_revalidation(
        self, repo, monkeypatch,
    ):
        branch = "feat/atomic-race"
        _git(["branch", branch, "main"], repo)
        record = next(item for item in worktree_gc.audit_branches(str(repo))
                      if item.name == branch)

        _git(["checkout", "-b", "race-source"], repo)
        (repo / "late.py").write_text("late = True\n")
        _git(["add", "late.py"], repo)
        _git(["commit", "-m", "late tip"], repo)
        late_tip = _git(["rev-parse", "HEAD"], repo)
        _git(["checkout", "main"], repo)
        _git(["branch", "-D", "race-source"], repo)

        real_git = worktree_gc._git
        injected = False

        def move_at_delete(args, cwd, timeout=15):
            nonlocal injected
            target = f"refs/heads/{branch}"
            if args[:3] == ["update-ref", "-d", target] and not injected:
                injected = True
                real_git(["update-ref", target, late_tip], cwd, timeout)
            return real_git(args, cwd, timeout)

        monkeypatch.setattr(worktree_gc, "_git", move_at_delete)
        actions = worktree_gc.reclaim_branches(str(repo), records=[record])

        assert _git(["rev-parse", branch], repo) == late_tip
        assert any("failed to delete" in action for action in actions)
