"""Windows Desktop shortcut branding contracts.

The packaged executable can contain the correct NousGirl resources while the
taskbar still displays Electron: Windows groups the process by
``com.nousresearch.hermes`` and can reuse an older pinned ``Electron.lnk`` with
the same AppUserModelID. The retarget script is the durable repair boundary
used after a canonical-main Desktop rebuild, so guard its source-level Windows
contract on every CI platform.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
RETARGET_PS1 = REPO_ROOT / "scripts" / "windows" / "Retarget-HermesDesktopShortcut.ps1"


def _read() -> str:
    return RETARGET_PS1.read_text(encoding="utf-8-sig")


def test_shortcuts_use_the_canonical_nousgirl_ico() -> None:
    source = _read()

    assert 'Join-Path $RepoRoot "apps\\desktop\\assets\\icon.ico"' in source
    assert 'Join-Path $RepoRoot ".venv\\Scripts\\hermes.exe"' not in source


def test_existing_start_menu_and_taskbar_aliases_are_retargeted() -> None:
    source = _read()

    assert '[Environment]::GetFolderPath("Programs")' in source
    assert 'Microsoft\\Internet Explorer\\Quick Launch\\User Pinned\\TaskBar' in source
    assert 'Join-Path $userPrograms "Electron.lnk"' in source
    assert 'Join-Path $taskbarPins "Electron.lnk"' in source
    assert 'if (Test-Path -LiteralPath $alias)' in source


def test_icon_refresh_is_non_destructive() -> None:
    source = _read()

    assert '& $iconRefresh -show' in source
    assert "Remove-Item" not in source
    assert "Stop-Process explorer" not in source
