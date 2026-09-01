from __future__ import annotations

from downstream.release_notes import render_release_notes


def test_release_notes_are_truthful_deterministic_and_complete() -> None:
    manifest = {
        "product_name": "Hermes Agent Windows Workstation Edition",
        "downstream_version": "0.21.0",
        "downstream_commit_sha": "a" * 40,
        "upstream_snapshot_sha": "b" * 40,
        "release_channel": "stable",
        "installer_signed": False,
        "attestation_status": "generated",
        "windows_qualification": {
            "status": "passed",
            "real_workstation_qualified": False,
        },
        "artifacts": [
            {"name": "setup.exe", "sha256": "c" * 64},
            {"name": "portable.zip", "sha256": "d" * 64},
        ],
    }
    notes = render_release_notes(
        manifest=manifest,
        features={
            "features": [
                {
                    "id": "windows-native-runtime",
                    "status": "verified",
                    "windows_required": True,
                }
            ]
        },
        carry={"carry": [{"id": "one"}]},
        adoption={
            "decision_counts": {"ADOPT": 2},
            "category_counts": {"SECURITY_CRITICAL": 1},
        },
        snapshot={"upstream_head_sha": "b" * 40},
        commits=[
            {
                "sha": "e" * 40,
                "subject": "fix windows desktop release",
                "paths": ["apps/desktop/release.ts"],
            }
        ],
        previous_tag=None,
    )

    for heading in (
        "Windows Workstation changes",
        "Upstream snapshot",
        "Security",
        "Bug fixes",
        "Local AI",
        "Desktop",
        "Memory",
        "Voice / VR / Unity",
        "Known limitations",
        "Artifact hashes",
    ):
        assert f"## {heading}" in notes
    assert "Installer signature: Unsigned" in notes
    assert "Physical workstation qualification: not recorded as passed" in notes
    assert f"Frozen upstream snapshot: `{'b' * 40}`" in notes
    assert f"`{'c' * 64}`  `setup.exe`" in notes
    assert "No earlier downstream Windows tag is recorded" in notes
    assert "latest Hermes" not in notes
