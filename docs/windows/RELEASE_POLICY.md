# Windows release policy

Official Hermes is the innovation stream. Hermes Agent Windows Workstation
Edition is a qualified downstream baseline for native Windows workstations.
The two projects retain separate release, issue, and support authorities.

## Frozen release trains

A release train starts from one exact upstream commit:

```text
upstream vX.Y.Z
  -> Windows vX.Y.Z-win.1
  -> Windows vX.Y.Z-win.2
```

The train may contain selected security backports, Windows-critical fixes, and
downstream feature fixes. It never follows moving upstream `main`. Every
manifest records the upstream SHA, downstream SHA, distribution version,
channel, architecture, artifact hashes, signing state, and qualification state.

## Stable and preview

`preview` permits candidate artifacts and incomplete physical-workstation
evidence. It must not be described as stable. A `stable` release requires all
of these gates at the exact tagged commit: install E2E, portable E2E, upgrade
E2E, native Windows Python, native Windows Desktop, Go watchdog, upstream API
compatibility, Windows regressions, and security locks.

Stable additionally requires recorded SHA-256 hashes, the frozen upstream SHA,
an exact qualification-SHA match, `ci_qualified: true`, and generated GitHub
artifact provenance. Real-workstation qualification is recorded independently
and is never inferred from GitHub-hosted runners.

## Publication

Main-branch pushes build and qualify preview artifacts but do not publish a
public GitHub Release. Only a version tag matching the distribution metadata,
such as `v0.20.5-win.1`, may publish the stable bundle. The release contains the
NSIS installer, portable ZIP, `release-manifest.json`, `SHA256SUMS.txt`, release
notes, qualification reports, and upgrade-baseline identity.

Authenticode signing is represented as observed. An unsigned installer remains
unsigned in the manifest and documentation; no self-signed certificate is
presented as trusted publisher identity.
