# Windows Distribution Release v1

Date: 2026-08-27

## Frozen scope

- Downstream start SHA: `8447bf369a0977b0dadf5c78896e194001dd1584`
- Frozen upstream snapshot SHA: `1fe0f2f3ac9748ce799272eb93bee2937b5ab802`
- Distribution version: `0.20.5-win.1`
- Implementation branch: `codex/distribution-windows-release-v1-20260827`
- Implementation worktree: isolated from the live primary checkout

The recorded upstream snapshot remained unchanged. This work did not fetch or
adopt a newer upstream `main` commit.

## Distribution contract

`downstream/distribution.json` is the product authority for the Windows
Workstation Edition. It defines the downstream repository, frozen upstream
snapshot, release version, supported architecture, platform tier, release
channels, and downstream-only update branch.

The CLI version surface, Windows bootstrap installers, Electron bootstrap, and
Tauri bootstrap all consume that authority. The downstream updater recognizes
the downstream origin as managed and fails closed when distribution metadata is
unavailable. It does not silently fall back to the official upstream archive.

## Packaging and release engineering

The Desktop package produces an NSIS installer and portable ZIP with downstream
product identity. The NSIS upgrade GUID preserves the previous application
identity so an installed Hermes version can be upgraded in place. Embedded PE
metadata records the display name, distribution identifier, and downstream
version.

The release bundle generator copies qualified artifacts into canonical names,
computes SHA-256 hashes, writes `release-manifest.json` and `SHA256SUMS.txt`, and
generates release notes from tracked manifests plus Git history. A stable bundle
is rejected unless every required gate passed for the exact downstream SHA,
`ci_qualified` is true, hashes and the upstream snapshot are present, and the
provenance attestation was generated.

The GitHub release workflow is SHA-pinned. A `main` push creates a non-publishing
preview qualification artifact. Only the tag matching the version authority may
publish a stable GitHub Release.

## Windows qualification

The qualification report includes these required release gates:

- `install_e2e`
- `portable_e2e`
- `upgrade_e2e`
- `windows_native_python`
- `windows_native_desktop`
- `watchdog_go`
- `upstream_api_compat`
- `windows_regression`
- `security_locks`

Installer E2E performs a silent non-administrator install into a path containing
spaces, validates embedded identity, launches the packaged Desktop, and runs the
uninstaller. Portable E2E extracts into a path containing spaces, validates the
standalone resource layout and identity, and launches without a developer
checkout. Upgrade E2E installs the baseline, writes profile data, upgrades in
place, proves the profile sentinel remains, validates the new identity, and
launches the upgraded Desktop.

Recursive cleanup is limited to a freshly generated, directly nested operating
system temporary directory whose name matches the qualification run type and
GUID. Only processes whose executable path belongs to that run are stopped.

## Local evidence before candidate publication

- Focused Python release, update, startup, and provider contracts: 49 passed
  after final environment-isolation hardening.
- Broader focused Python qualification set: 112 passed.
- Electron distribution/bootstrap tests: 13 passed.
- PE identity test: 1 passed.
- Desktop TypeScript typecheck: passed.
- Desktop build: passed.
- Go watchdog tests: passed.
- Changed PowerShell scripts: parser passed.
- Installer E2E: passed against the built `0.20.5-win.1` artifact.
- Portable E2E: passed against the built `0.20.5-win.1` artifact.
- Upgrade E2E: passed from the recorded downstream start build to the current
  artifact with profile data preserved.
- Integrated local qualification: all nine required gates passed. The report
  correctly records `executed_in_ci: false` and `ci_qualified: false`; local
  execution is not promoted into cloud CI evidence.

The locally built installer reported Authenticode status `NotSigned`. The
manifest and documentation preserve that fact. No self-signed or fabricated
publisher identity is used.

## Real workstation evidence boundary

The privacy-safe collector records Windows and GPU facts, exact SHAs, artifact
identity and hash, matching Desktop distribution identity, loopback health, and
explicit sleep/resume and physical restart results. It does not record usernames,
executable paths, model paths, command lines, secrets, prompts, or sessions.

The partial local report observed Windows 11 Pro and an NVIDIA RTX 5060 Ti with
16,311 MiB reported VRAM. Backend and watchdog health passed, but no running
Desktop process matched the candidate distribution identity. Llama and embedding
health did not pass, while sleep/resume and physical restart were not run.
Accordingly, real-workstation qualification remains failed and must not be
inferred from native Windows CI.

## Rollback and recovery

The release changes are isolated on the implementation branch until exact-head
checks pass. The downstream updater retains the existing transactional plan,
snapshot, apply, restart, verify, and receipt stages. Installer E2E uses isolated
temporary roots, and upgrade E2E preserves profile data independently from the
installation directory.

A published release can be rolled back by reinstalling the previous qualified
installer or portable artifact using its recorded hash. Upstream adoption remains
a separate, explicit compatibility decision against the frozen snapshot.

## Publication evidence authority

Candidate, `main`, and stable-release verdicts are exact-SHA claims. Their final
evidence is the GitHub checks and release object for that SHA, plus the release
manifest, qualification report, hashes, and provenance attestation. A passing
parent commit, unrelated pull request, or local-only run is not publication
evidence.
