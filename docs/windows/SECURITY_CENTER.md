# Windows Security Center

Hermes Security Center is a local workstation protection surface for file scanning, definition state, user-space monitoring, detection evidence, and encrypted quarantine. It complements the existing `hermes security audit` supply-chain audit; it does not replace Windows Defender, an EDR product, or a kernel file-system filter.

The implementation is intentionally deterministic. Language models do not select verdicts, modify evidence, restore files, delete quarantine items, or disable monitoring. Scanner evidence is stored under the active profile at `<HERMES_HOME>/security/security.db` in SQLite WAL mode.

## Commands

```powershell
hermes security status --json
hermes security scan C:\path\to\file --json
hermes security scan --quick --json
hermes security scan --full --json
hermes security update --json
hermes security feeds --json
hermes security watch status --json
hermes security watch enable --json
hermes security watch disable --json
hermes security quarantine list --json
```

The Desktop Security Center reads the same profile-scoped REST API and evidence database as the CLI. Mutating API calls require an explicit `confirmed=true` field or query parameter. The Desktop presents a confirmation dialog before it sends that field.

## Scheduled scans

Scheduled scans compose with Hermes' existing cron authority instead of introducing a second scheduler. An operator can create a daily quick scan with a self-contained job such as:

```powershell
hermes cron create "17 3 * * *" "Run hermes security scan --quick --json locally. Report only non-clean results with their exact verdict and evidence; do not restore or delete quarantine items." --name "Daily security quick scan"
```

Choose a different minute for each profile or workstation to provide update and scan jitter. Scheduled jobs inherit the cron subsystem's bounded runtime and audit behavior; Security Center does not silently create a schedule or grant an agent permission to restore or permanently delete items.

## Protection boundaries

Quick scan covers existing Downloads, Desktop, temporary and Startup directories for the current user plus profile-scoped Hermes plugin and skill directories. Custom scan covers explicit Hermes workspaces. Full scan enumerates local Windows drive roots. Directory traversal does not follow symbolic links or directory junctions and uses a bounded worker pool.

The watcher is a below-normal-priority user-space reconciliation process. It periodically compares file size and modification time in the quick-scan locations, then sends changed files through the same scan pipeline. It is not a kernel minifilter and cannot claim pre-write or pre-open interception. Phase 1 does not claim USN Journal gap-free coverage; periodic reconciliation is the recovery boundary.

The terminal execution boundary inspects explicit local executable, script, archive, and package paths before a local command runs. A high-confidence malicious verdict blocks execution. Suspicious, unknown, and scanner-error results retain their exact verdict and are logged as warnings rather than being mislabeled clean.

## Operational status

Security Center reports unavailable engines and failed definition updates as typed states. A missing ClamAV or YARA installation is not rendered as protected. Operators should qualify the Windows host with current definitions and the EICAR test before describing the workstation as protected by Hermes anti-malware.
