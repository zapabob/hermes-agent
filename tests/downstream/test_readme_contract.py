from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_readme_has_downstream_identity_and_attribution() -> None:
    assert README.startswith("# Hermes Agent Windows Workstation Edition\n")
    assert "Windows-first downstream distribution of Hermes Agent." in README
    assert "This is an unofficial downstream distribution." in README
    assert "It is not affiliated with or endorsed by Nous Research." in README
    assert (
        "Original Hermes Agent is developed by Nous Research and licensed under MIT."
        in README
    )


def test_readme_uses_required_section_order() -> None:
    headings = [
        "## 1. Product identity",
        "## 2. Windows-first goals",
        "## 3. Who this is for",
        "## 4. Downstream advantages",
        "## 5. Verified feature matrix",
        "## 6. Windows Tier-1 support contract",
        "## 7. Local AI architecture",
        "## 8. Watchdog and recovery architecture",
        "## 9. Memory and semantic retrieval",
        "## 10. VRChat, Unity, and voice integrations",
        "## 11. Installation",
        "## 12. Update and upstream integration policy",
        "## 13. Architecture",
        "## 14. Security",
        "## 15. Upstream project",
        "## 16. License and attribution",
    ]
    positions = [README.index(heading) for heading in headings]
    assert positions == sorted(positions)


def test_readme_exposes_verified_windows_install_surfaces() -> None:
    assert "git clone https://github.com/zapabob/hermes-agent-windows.git" in README
    assert "https://github.com/zapabob/hermes-agent-windows/releases" in README
    assert "installer" in README.lower()
    assert "portable" in README.lower()
    assert "0.20.5-win.1" in README
    assert "docs/windows/INSTALL.md" in README
    assert "curl -fsSL https://raw.githubusercontent.com/NousResearch" not in README
    assert "official upstream installer" in README.lower()


def test_readme_preserves_upstream_identity() -> None:
    assert "https://github.com/NousResearch/hermes-agent" in README
    assert "official Windows edition" not in README
    assert "world's largest" not in README


def test_translated_readmes_keep_distribution_metadata_in_parity() -> None:
    for name in ("README.md", "README.ja.md", "README.zh-CN.md"):
        content = (ROOT / name).read_text(encoding="utf-8")
        for value in (
            "Hermes Agent Windows Workstation Edition",
            "zapabob/hermes-agent-windows",
            "NousResearch/hermes-agent",
            "0.20.5-win.1",
            "stable",
            "preview",
            "docs/windows/INSTALL.md",
        ):
            assert value in content, f"{name}: {value}"
