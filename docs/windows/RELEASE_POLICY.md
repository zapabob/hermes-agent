# Windows release policy

Official Hermes is the innovation stream. Hermes Agent Windows Workstation
Edition is a qualified downstream baseline for native Windows workstations.
The two projects retain separate release, issue, and support authorities.

## Upstream-aligned release trains

A release train starts from one exact official release and retains its semantic
version without a downstream suffix:

```text
official Hermes vX.Y.Z
  -> Windows qualification at vX.Y.Z
  -> downstream revision identified by its commit SHA
```

The train may contain selected security backports, Windows-critical fixes, and
downstream feature fixes. It never follows moving upstream `main`, and it does
not mint an independent semantic-version series. Every manifest records the
official version and release commit, frozen upstream SHA, downstream SHA,
channel, architecture, artifact hashes, signing state, and qualification state.
The official release history and changelog are the version authority.

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
public GitHub Release. Only a version tag matching the official-form
distribution metadata, such as `v0.21.0`, may publish the stable bundle. The
release contains the
NSIS installer, portable ZIP, `release-manifest.json`, `SHA256SUMS.txt`, release
notes, qualification reports, and upgrade-baseline identity.

Authenticode signing is represented as observed. An unsigned installer remains
unsigned in the manifest and documentation; no self-signed certificate is
presented as trusted publisher identity.
