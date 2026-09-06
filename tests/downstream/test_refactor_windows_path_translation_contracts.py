from __future__ import annotations

import pytest

from downstream.platform.windows.paths import translate_msys_drive_path

# CodeGraph Wave1: impact translate_msys_drive_path=25 (shared core frozen).
# Wrappers may diverge on historical bare-drive spellings — pin that gap.
# Semantic equivalence gate: overlapping drive fixtures must match the core.


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/c/Users/NVIDIA", r"C:\Users\NVIDIA"),
        ("/C/Users/foo", r"C:\Users\foo"),
        ("/d/Projects/foo bar", r"D:\Projects\foo bar"),
        ("/mnt/c/Users", r"C:\Users"),
        ("/cygdrive/d/data", r"D:\data"),
        ("/c", "C:\\"),
    ],
)
def test_translate_msys_drive_path_native_forms(raw: str, expected: str) -> None:
    assert translate_msys_drive_path(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "/home/teknium",
        "/tmp/foo",
        r"C:\Users\foo",
        "C:/Users/foo",
        "relative/path",
        "",
    ],
)
def test_translate_msys_drive_path_leaves_non_drive_spellings(raw: str) -> None:
    assert translate_msys_drive_path(raw) is None


def test_sensitivity_home_must_not_become_drive_path() -> None:
    """If the regex wrongly treats /home as /h + ome, translation must fail closed."""
    assert translate_msys_drive_path("/home/teknium") is None


@pytest.mark.windows_only
@pytest.mark.parametrize(
    "bare",
    ["/c", "/C", "/mnt/c", "/cygdrive/d"],
)
def test_cli_wrapper_preserves_historical_bare_drive_noops(bare: str) -> None:
    """cli._normalize_git_bash_path keeps bare drive roots unchanged.

    CodeGraph impact _normalize_git_bash_path=6. Collapsing into the shared
    core's ``C:\\`` mapping would change observable CLI path resolution.
    """
    from cli import _normalize_git_bash_path

    assert _normalize_git_bash_path(bare) == bare


@pytest.mark.windows_only
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/c", "C:\\"),
        ("/mnt/c", "C:\\"),
        ("/cygdrive/d", "D:\\"),
        ("/c/Users/NVIDIA", r"C:\Users\NVIDIA"),
    ],
)
def test_local_wrapper_delegates_bare_and_drive_forms(
    raw: str, expected: str
) -> None:
    """local._msys_to_windows_path maps bare drives via the shared core."""
    from tools.environments.local import _msys_to_windows_path

    assert _msys_to_windows_path(raw) == expected


@pytest.mark.windows_only
def test_wrapper_divergence_on_bare_drive_is_intentional() -> None:
    """Freeze the known CLI vs local bare-``/c`` policy split (Wave1 ledger)."""
    from cli import _normalize_git_bash_path
    from tools.environments.local import _msys_to_windows_path

    assert _normalize_git_bash_path("/c") == "/c"
    assert _msys_to_windows_path("/c") == "C:\\"
    assert translate_msys_drive_path("/c") == "C:\\"


@pytest.mark.windows_only
@pytest.mark.parametrize(
    "raw",
    [
        "/c/Users/NVIDIA",
        "/mnt/c/Users",
        "/cygdrive/d/data",
        "/home/teknium",
    ],
)
def test_wrappers_match_core_on_overlapping_fixtures(raw: str) -> None:
    """Semantic equivalence: wrappers agree with the core except CLI bare no-ops."""
    from cli import _normalize_git_bash_path
    from tools.environments.local import _msys_to_windows_path

    core = translate_msys_drive_path(raw)
    expected_local = core if core is not None else raw
    assert _msys_to_windows_path(raw) == expected_local
    # CLI applies historical bare-drive no-ops then delegates.
    if raw in {"/c", "/C", "/mnt/c", "/cygdrive/d"}:
        assert _normalize_git_bash_path(raw) == raw
    else:
        expected_cli = core if core is not None else raw
        assert _normalize_git_bash_path(raw) == expected_cli
