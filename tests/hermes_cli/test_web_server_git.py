import subprocess
from pathlib import Path

import pytest

from hermes_cli import web_server

pytest.importorskip("starlette.testclient")
from starlette.testclient import TestClient


@pytest.fixture
def client():
    previous = getattr(web_server.app.state, "auth_required", None)
    web_server.app.state.auth_required = False
    test_client = TestClient(web_server.app)
    test_client.headers[web_server._SESSION_HEADER_NAME] = web_server._SESSION_TOKEN
    try:
        yield test_client
    finally:
        if previous is None:
            try:
                delattr(web_server.app.state, "auth_required")
            except AttributeError:
                pass
        else:
            web_server.app.state.auth_required = previous


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "a.txt").write_text("one\ntwo\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    # A tracked modification + a brand-new untracked file (the new-file case the
    # rail/review must surface).
    (root / "a.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
    (root / "new.py").write_text("print(1)\nprint(2)\n", encoding="utf-8")
    return root










def test_stage_commit_roundtrip_clears_changes(client, repo):
    assert client.post("/api/git/review/stage", json={"path": str(repo), "file": "a.txt"}).json() == {"ok": True}
    staged = client.get("/api/git/status", params={"path": str(repo)}).json()
    assert staged["staged"] >= 1

    assert client.post(
        "/api/git/review/commit", json={"path": str(repo), "message": "tracked change", "push": False}
    ).json() == {"ok": True}

    after = client.get("/api/git/status", params={"path": str(repo)}).json()
    # The tracked change is committed; only the untracked file remains.
    assert after["changed"] == 1
    assert after["untracked"] == 1


def test_git_history_routes_return_commit_metadata_and_selected_diff(client, repo):
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-qm", "add third line")

    history = client.get("/api/git/review/history", params={"path": str(repo), "limit": 2})

    assert history.status_code == 200
    commits = history.json()["commits"]
    assert len(commits) == 2
    assert commits[0]["subject"] == "add third line"
    assert commits[1]["subject"] == "init"
    assert len(commits[0]["sha"]) == 40
    assert commits[0]["parents"]

    diff = client.get(
        "/api/git/review/history-diff", params={"path": str(repo), "sha": commits[0]["sha"]}
    )

    assert diff.status_code == 200
    assert "+three" in diff.json()["diff"]

    invalid = client.get("/api/git/review/history-diff", params={"path": str(repo), "sha": "HEAD~1"})
    assert invalid.status_code == 200
    assert invalid.json() == {"diff": ""}






def test_worktree_add_initializes_plain_folder(client, tmp_path):
    folder = tmp_path / "plain-project"
    folder.mkdir()
    (folder / "notes.txt").write_text("not committed\n", encoding="utf-8")

    added = client.post(
        "/api/git/worktree/add", json={"path": str(folder), "branch": "feature/plain"}
    ).json()

    assert added["branch"] == "feature/plain"
    assert Path(added["path"]).is_dir()
    assert (folder / ".git").exists()
    _git(folder, "rev-parse", "--verify", "HEAD")

    status = client.get("/api/git/status", params={"path": str(folder)}).json()
    assert status["branch"] == status["defaultBranch"]
    assert status["branch"]
    # Existing files are not silently committed by repo initialization.
    assert any(file["path"] == "notes.txt" and file["untracked"] for file in status["files"])




def test_git_endpoints_require_auth(repo):
    unauth = TestClient(web_server.app)

    assert unauth.get("/api/git/status", params={"path": str(repo)}).status_code == 401
    assert unauth.post("/api/git/review/stage", json={"path": str(repo)}).status_code == 401


# ── remote-gateway worktree parity (#81724) ─────────────────────────────────
# The desktop's Electron git ops learned remote-branch conversion and
# no-upstream-tracking base branching; the backend REST mirror (what a remote
# gateway serves) must behave identically or worktree flows break exactly and
# only on remote connections.


@pytest.fixture
def repo_with_remote(tmp_path):
    """A committed repo with an `origin` remote carrying main + a feature
    branch that has NO local head (the teammate-branch case)."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True, capture_output=True)

    root = tmp_path / "clone"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "a.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    _git(root, "remote", "add", "origin", str(origin))
    _git(root, "push", "-q", "origin", "main")
    _git(root, "branch", "feature")
    _git(root, "push", "-q", "origin", "feature")
    _git(root, "branch", "-D", "feature")
    _git(root, "fetch", "-q", "origin")
    return root


def test_branches_include_remote_tracking_refs(client, repo_with_remote):
    branches = client.get(
        "/api/git/branches", params={"path": str(repo_with_remote)}
    ).json()["branches"]
    by_name = {branch["name"]: branch for branch in branches}

    # A teammate's branch (no local head) is reachable, flagged as remote.
    assert "origin/feature" in by_name
    assert by_name["origin/feature"]["isRemote"] is True
    assert by_name["origin/feature"]["checkedOut"] is False
    assert by_name["origin/feature"]["worktreePath"] is None

    # Locals carry the flag too, and shadowed remotes/HEAD aliases are noise.
    assert by_name["main"]["isRemote"] is False
    assert "origin/main" not in by_name
    assert all(not branch["name"].endswith("/HEAD") for branch in branches)


def test_worktree_add_existing_remote_branch_tracks_not_detaches(client, repo_with_remote):
    added = client.post(
        "/api/git/worktree/add",
        json={"path": str(repo_with_remote), "existingBranch": "origin/feature"},
    ).json()

    # A remote-tracking ref cannot be checked out directly — the mirror must
    # create the local tracking branch, like `git switch feature` would.
    assert added["branch"] == "feature"
    tree = Path(added["path"])
    assert tree.is_dir()

    head = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=tree, check=True, capture_output=True, text=True,
    ).stdout.strip()
    assert head == "feature"  # NOT detached

    upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "feature@{upstream}"],
        cwd=tree, check=True, capture_output=True, text=True,
    ).stdout.strip()
    assert upstream == "origin/feature"


def test_worktree_add_from_origin_base_does_not_track(client, repo_with_remote):
    added = client.post(
        "/api/git/worktree/add",
        json={"path": str(repo_with_remote), "branch": "fresh", "base": "origin/main"},
    ).json()
    assert added["branch"] == "fresh"

    # Branching off origin/main must yield a standalone local branch, not one
    # silently wired to the remote's upstream (parity with the Electron op).
    probe = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "fresh@{upstream}"],
        cwd=repo_with_remote, capture_output=True, text=True,
    )
    assert probe.returncode != 0


# ── remote-gateway SCM rail parity (#82793) ─────────────────────────────────
# The Electron SCM rail (branches/tags/stashes CRUD + fetch/pull) runs as
# Electron-local git; on a remote gateway the backend REST mirror must behave
# identically — same shapes, same validation, same failure semantics.


def test_tags_route_lists_peeled_and_lightweight_tags(client, repo):
    _git(repo, "tag", "v1")  # lightweight -> the commit sha itself
    _git(repo, "tag", "-a", "v2", "-m", "release two")  # annotated -> peeled

    tags = client.get("/api/git/tags", params={"path": str(repo)}).json()["tags"]
    by_name = {tag["name"]: tag for tag in tags}

    assert by_name["v1"]["sha"] and by_name["v2"]["sha"]
    # Annotated tag subject is its message; a lightweight tag has no message
    # of its own, so git reports the commit's subject.
    assert by_name["v1"]["subject"] == "init"
    assert by_name["v2"]["subject"] == "release two"
    assert all(tag["shortSha"] == tag["sha"][:7] for tag in tags)


def test_stashes_route_lists_newest_first_with_indices(client, repo):
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-qm", "tracked")
    (repo / "a.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
    _git(repo, "stash", "push", "-m", "wip one")
    (repo / "a.txt").write_text("one\ntwo\nthree\nfour\nfive\n", encoding="utf-8")
    _git(repo, "stash", "push", "-m", "wip two")

    stashes = client.get("/api/git/stashes", params={"path": str(repo)}).json()["stashes"]

    # Newest stash first, with stable indices the drop/apply route can use.
    assert [stash["index"] for stash in stashes] == [0, 1]
    assert all(stash["message"].endswith(note) for stash, note in zip(stashes, ["wip two", "wip one"]))
    assert all(len(stash["sha"]) == 40 for stash in stashes)


def test_scm_rail_branch_mutations_validate_names(client, repo):
    assert client.post(
        "/api/git/branch/create", json={"path": str(repo), "name": "feature/x"}
    ).json() == {"ok": True}

    # git's own ref grammar at the boundary — never a silent sanitizer.
    invalid = client.post(
        "/api/git/branch/create", json={"path": str(repo), "name": "bad name"}
    )
    assert invalid.status_code == 400

    assert client.post(
        "/api/git/branch/rename",
        json={"path": str(repo), "name": "feature/x", "newName": "feature/y"},
    ).json() == {"ok": True}
    assert client.post(
        "/api/git/branch/delete", json={"path": str(repo), "name": "feature/y"}
    ).json() == {"ok": True}


def test_scm_rail_tag_mutations_roundtrip(client, repo):
    assert client.post(
        "/api/git/tag/create", json={"path": str(repo), "name": "v1", "target": "HEAD"}
    ).json() == {"ok": True}
    assert client.post(
        "/api/git/tag/delete", json={"path": str(repo), "name": "v1"}
    ).json() == {"ok": True}


def test_scm_rail_stash_create_apply_drop_roundtrip(client, repo):
    (repo / "a.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
    assert client.post(
        "/api/git/stash/create",
        json={"path": str(repo), "message": "wip", "includeUntracked": True},
    ).json() == {"ok": True}

    stashes = client.get("/api/git/stashes", params={"path": str(repo)}).json()["stashes"]
    assert len(stashes) == 1
    index = stashes[0]["index"]

    assert client.post(
        "/api/git/stash/apply", json={"path": str(repo), "index": index}
    ).json() == {"ok": True}
    assert client.post(
        "/api/git/stash/drop", json={"path": str(repo), "index": index}
    ).json() == {"ok": True}
    assert client.get("/api/git/stashes", params={"path": str(repo)}).json()["stashes"] == []


def test_scm_rail_fetch_and_pull(client, tmp_path):
    origin = tmp_path / "origin.git"
    origin.mkdir()
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True, capture_output=True)
    # `git init --bare` points HEAD at refs/heads/master by default; point it
    # at main so `git clone` actually checks out (a bare HEAD pointing at a
    # branch that will exist later leaves the clone without a working tree).
    subprocess.run(
        ["git", "--git-dir", str(origin), "symbolic-ref", "HEAD", "refs/heads/main"],
        check=True, capture_output=True,
    )

    root = tmp_path / "clone"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "a.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    _git(root, "remote", "add", "origin", str(origin))
    # `-u` so the plain `git pull` the mirror runs has an upstream to follow,
    # exactly like a repo that was actually cloned.
    _git(root, "push", "-u", "-q", "origin", "main")

    peer = tmp_path / "peer"
    peer.mkdir()
    subprocess.run(["git", "clone", "-q", str(origin), str(peer)], check=True, capture_output=True)
    (peer / "b.txt").write_text("two\n", encoding="utf-8")
    _git(peer, "add", "-A")
    _git(peer, "commit", "-qm", "peer commit")
    _git(peer, "push", "-q", "origin", "main")

    assert client.post(
        "/api/git/fetch", json={"path": str(root), "remote": "origin"}
    ).json() == {"ok": True}
    assert client.post(
        "/api/git/pull", json={"path": str(root), "rebase": False}
    ).json() == {"ok": True}

    head = subprocess.run(
        ["git", "log", "-1", "--format=%s"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    assert head == "peer commit"
