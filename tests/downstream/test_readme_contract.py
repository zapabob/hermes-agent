from __future__ import annotations

from pathlib import Path

README = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")


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


def test_readme_installs_the_fork_from_source_only() -> None:
    assert "git clone https://github.com/zapabob/hermes-agent-windows.git" in README
    assert "no verified fork-specific binary installer" in README
    assert "curl -fsSL https://raw.githubusercontent.com/NousResearch" not in README
    assert "official upstream installer" in README.lower()


def test_readme_preserves_upstream_identity() -> None:
    assert "https://github.com/NousResearch/hermes-agent" in README
    assert "official Windows edition" not in README
    assert "world's largest" not in README
