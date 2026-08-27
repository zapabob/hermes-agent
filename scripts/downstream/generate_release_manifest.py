from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any

from downstream.distribution import load_distribution, resolve_downstream_sha
from downstream.release_notes import build_release_notes


REQUIRED_STABLE_GATES = (
    "install_e2e",
    "portable_e2e",
    "upgrade_e2e",
    "windows_native_python",
    "windows_native_desktop",
    "watchdog_go",
    "upstream_api_compat",
    "windows_regression",
    "security_locks",
)
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(path: Path, kind: str, *, signed: bool | None = None) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "kind": kind,
        "name": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }
    if signed is not None:
        artifact["signed"] = signed
    return artifact


def _validate_qualification(
    qualification: dict[str, Any], channel: str, downstream_sha: str
) -> None:
    if channel != "stable":
        return
    gates = qualification.get("gates", {})
    missing = [name for name in REQUIRED_STABLE_GATES if gates.get(name) != "passed"]
    sha_matches = qualification.get("downstream_commit_sha") == downstream_sha
    ci_qualified = qualification.get("ci_qualified") is True
    if (
        qualification.get("status") != "passed"
        or missing
        or not sha_matches
        or not ci_qualified
    ):
        if not sha_matches:
            missing.append("exact_downstream_sha")
        if not ci_qualified:
            missing.append("ci_qualified")
        details = ", ".join(missing) if missing else "overall status"
        raise ValueError(
            f"stable release requires passed qualification gates: {details}"
        )


def generate_release_bundle(
    *,
    installer: Path,
    portable: Path,
    qualification: dict[str, Any],
    output_dir: Path,
    channel: str,
    downstream_sha: str,
    installer_signed: bool,
    build_timestamp_utc: str | None = None,
    attestation_status: str = "not_generated",
) -> dict[str, Any]:
    distribution = load_distribution()
    if channel not in distribution.channels.supported:
        raise ValueError(f"unsupported release channel: {channel}")
    if not FULL_SHA.fullmatch(downstream_sha):
        raise ValueError("downstream SHA must be a 40-character lowercase SHA")
    if not installer.is_file() or not portable.is_file():
        raise FileNotFoundError("installer and portable artifacts are required")
    _validate_qualification(qualification, channel, downstream_sha)
    if channel == "stable" and attestation_status != "generated":
        raise ValueError("stable release requires generated provenance attestation")

    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"Hermes-Agent-Windows-{distribution.version}-x64"
    published_installer = output_dir / f"{prefix}-Setup.exe"
    published_portable = output_dir / f"{prefix}-portable.zip"
    shutil.copy2(installer, published_installer)
    shutil.copy2(portable, published_portable)

    artifacts = [
        _artifact(published_installer, "installer", signed=installer_signed),
        _artifact(published_portable, "portable"),
    ]
    timestamp = build_timestamp_utc or datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "product_name": distribution.display_name,
        "distribution_id": distribution.id,
        "downstream_version": distribution.version,
        "downstream_commit_sha": downstream_sha,
        "upstream_snapshot_sha": distribution.upstream.snapshot_sha,
        "build_timestamp_utc": timestamp,
        "release_channel": channel,
        "architecture": distribution.platform.architectures[0],
        "artifacts": artifacts,
        "installer_signed": installer_signed,
        "portable_artifact": published_portable.name,
        "windows_qualification": {
            "status": qualification.get("status", "unknown"),
            "schema_version": qualification.get("schema_version", 0),
            "ci_qualified": qualification.get("ci_qualified", False),
            "real_workstation_qualified": qualification.get(
                "real_workstation_qualified", False
            ),
        },
        "attestation_status": attestation_status,
    }

    manifest_path = output_dir / "release-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sums = "".join(f"{item['sha256']}  {item['name']}\n" for item in artifacts)
    (output_dir / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")
    (output_dir / "RELEASE_NOTES.md").write_text(
        build_release_notes(manifest, Path(__file__).resolve().parents[2]),
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--portable", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--channel", choices=("stable", "preview"), required=True)
    parser.add_argument("--downstream-sha", default="")
    parser.add_argument("--installer-signed", choices=("true", "false"), required=True)
    parser.add_argument("--attestation-status", default="not_generated")
    args = parser.parse_args()

    qualification = json.loads(args.qualification.read_text(encoding="utf-8"))
    downstream_sha = args.downstream_sha or resolve_downstream_sha()
    if not downstream_sha:
        raise SystemExit("could not resolve downstream commit SHA")
    generate_release_bundle(
        installer=args.installer,
        portable=args.portable,
        qualification=qualification,
        output_dir=args.output_dir,
        channel=args.channel,
        downstream_sha=downstream_sha,
        installer_signed=args.installer_signed == "true",
        attestation_status=args.attestation_status,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
