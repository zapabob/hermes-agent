"""Regression coverage for the Windows Go-watchdog hidden launch contract."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WINDOWS_SCRIPTS = REPO_ROOT / "scripts" / "windows"


def _read(name: str) -> str:
    return (WINDOWS_SCRIPTS / name).read_text(encoding="utf-8")


def test_watchdog_binary_uses_the_windows_gui_subsystem() -> None:
    build_script = _read("Build-HermesGoWatchdog.ps1")

    assert '-ldflags "-s -w -H=windowsgui"' in build_script


def test_watchdog_launch_paths_remain_hidden() -> None:
    launcher = _read("Start-HermesGoWatchdog.ps1")
    autostart = _read("Register-HermesFullAutostart.ps1")

    assert "-WindowStyle Hidden -PassThru" in launcher
    assert (
        "$startInfo.WindowStyle = "
        "[System.Diagnostics.ProcessWindowStyle]::Hidden"
    ) in launcher
    assert "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass" in autostart
