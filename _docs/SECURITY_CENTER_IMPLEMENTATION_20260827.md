# Hermes Windows Security Center Implementation Record

Date: 2026-08-27

Base revision: `8447bf369a0977b0dadf5c78896e194001dd1584`

Implementation branch: `codex/security-center-20260827`

## Delivered boundary

This change adds a downstream-owned, profile-scoped defensive malware subsystem under `downstream/security/`. It preserves the existing `hermes security audit` command and adds local scan, status, feed update, watcher, quarantine, restore, and delete operations through the CLI, authenticated local API, and Electron Desktop Security Center.

The decision boundary is deterministic. Local SHA-256 reputation scores 100, ClamAV detections score 90, curated core YARA detections score 80, extended YARA detections score 60, and static heuristics score 20. Language-model output is not consulted when producing a verdict or authorizing a side effect.

## Data, privacy, and recovery contracts

The profile database is `<HERMES_HOME>/security/security.db` in SQLite WAL mode. It stores feed state, canonical SHA-256 reputation, locally cached IOCs, versioned scan evidence, allowlist actions, quarantine metadata, and durable audit events. Existing early Security Center databases receive additive in-place column migrations; user evidence is not discarded.

No local file content or hash is submitted to an external service. ClamAV updates use `freshclam`; YARA and reputation lookups are local. Optional public feed catalogue entries preserve source, licensing, attribution, and update metadata. Malware samples are neither downloaded nor executed.

Quarantine uses opaque UUID blobs encrypted with AES-256-GCM. The 256-bit vault key is protected with Windows DPAPI and restricted to the owning user and LocalSystem. The source identity is checked during hashing and again during quarantine. The encrypted blob is authenticated and its plaintext SHA-256 is verified before the source is removed. Restore authenticates, verifies, rescans without cache, refuses overwrite, requires an explicit override for a still-malicious result, and restores recorded access and modification times.

## Execution and monitoring boundary

The local terminal boundary scans explicit executable, script, package, and archive arguments. High-confidence malicious evidence blocks execution; suspicious and scanner-error evidence remains visible without being renamed clean. Existing plugin and skill authorization remains the trust authority.

The Phase 1 watcher is a below-normal-priority user-space reconciliation process. It creates a metadata baseline before reporting ready, then scans only newly created or changed files at a bounded interval. It does not scan all pre-existing Temp content at startup, follow reparse points, claim a kernel minifilter, or claim gap-free USN Journal coverage. The external Hermes watchdog remains the outer supervisor.

Scheduled scans compose with the existing Hermes cron subsystem. Security Center does not silently create schedules or grant an agent permission to restore or delete quarantine objects.

## Desktop fidelity ledger

The generated concept is `_docs/security-center/security-center-concept.png`; the qualified Electron surface is `_docs/security-center/security-center-manual-qa.png`.

1. The Security Center uses a dedicated shield entry in the existing primary sidebar, matching the concept's persistent navigation placement.
2. The surface uses the existing Desktop typography and theme tokens, with flat section dividers instead of invented card chrome.
3. Protection, engine, and feed states use compact status dots and exact state strings; unavailable ClamAV is shown as `scanner_unavailable`, never as protected.
4. Summary metrics, scan actions, recent evidence, and encrypted quarantine follow the concept's information hierarchy without fabricating counts or signature freshness.
5. Detection and quarantine tables expose exact SHA-256, ClamAV, or YARA evidence from durable event metadata.
6. The responsive layout is based on the actual pane width. Its auto-fit grid remains usable in the 268-pixel workspace seen in the real multi-pane Electron shell.
7. The concept's dark appearance is not forced. The implementation inherits the user's active Desktop theme and retains the same hierarchy in light or dark mode.

## Qualification evidence

Local focused qualification before publication:

- Python security, terminal enforcement, and legacy audit contracts: 55 passed, with one real-ClamAV test skipped because ClamAV is not installed on this workstation.
- Expanded security kernel coverage includes clean, EICAR, known SHA-256, YARA, heuristic-only, scanner-timeout, corrupt-update rollback, encryption, tamper rejection, exact restore, no-overwrite, Windows ACL, spaces, Unicode, reparse avoidance, unreadable file, large file, archive, concurrency, watcher reconciliation, and schema migration contracts.
- Desktop Security Center UI tests: 3 passed.
- Desktop TypeScript typecheck: passed.
- Changed Desktop ESLint scope: zero errors and zero warnings.
- Production Electron/Vite build: passed, including native dependency staging and built-artifact assertion.
- Electron Security Center E2E: passed in the real multi-pane shell with no error banners and exact unavailable-scanner evidence.
- Wheel build under the repository's official `HERMES_NIX_BUILD=1` boundary: passed; the wheel contains the downstream package, feed catalogue, and bundled YARA rule.
- ClamAV adapter fallback contract: a failed `clamdscan` connection falls back to `clamscan` with the managed database directory.
- Workflow YAML and its embedded PowerShell installer block: parsed successfully.
- `uv lock --check`: passed.

Manual Windows watcher qualification used only a harmless local YARA marker inside the isolated worktree. After the watcher reported ready, one new file was created. The watcher produced one scan, classified the core-rule match as `MALICIOUS`, encrypted and quarantined it, removed the source only after vault verification, and then stopped cleanly.

The exact-head GitHub Actions result belongs to the immutable `origin/main` revision created after this record is committed. The final delivery report must identify that SHA and its completed workflow run; a local pass is not represented as cloud CI evidence.

## Rollback

Disable monitoring first with `hermes security watch disable`. Revert the published implementation commit with a normal `git revert`; do not reset the shared main branch. Existing encrypted quarantine blobs and `security.db` remain profile data and are not deleted by a code rollback. Restore or delete individual quarantine objects only through the explicit CLI/Desktop confirmation paths. If a definition activation fails, the updater retains the prior working database automatically.

## Known boundary

This is layered local malware protection, not a claim of complete detection, EDR replacement, kernel on-access antivirus, or USN gap-free coverage. Local ClamAV qualification remains intentionally unclaimed on this workstation; the Windows CI lane is configured to install ClamAV, update official databases, require the adapter, run EICAR plus clean negative controls, and fail when ClamAV is unavailable.
