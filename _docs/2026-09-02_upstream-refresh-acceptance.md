# Hermes Agent upstream refresh acceptance

Date: 2026-09-02
Official source: `NousResearch/hermes-agent`
Downstream: `zapabob/hermes-agent-windows`
Frozen upstream commit: `5a8e8a6b87487c0e0785cd9eb561cc6a96c64f5e`
Downstream start: `2c9e426a59c02a6bbe7f9beab9fbfdf081e24bd7`
Official release version: `0.21.0`

## Acceptance decision

The refresh is accepted as a semantic integration. Official behavior was adopted where it fits the downstream architecture, composed with Windows-specific and local-runtime capabilities where both are required, and excluded where it is platform-specific or generated material. The integration does not replace the downstream tree wholesale and does not weaken its Windows process, profile-isolation, local-model, memory, operator, or update-safety contracts.

## Adoption matrix

| UPSTREAM ITEM | STATUS | DOWNSTREAM IMPLEMENTATION | TEST | COMMIT |
|---|---|---|---|---|
| Frozen official source inventory and comparison metadata | ADOPTED | Records the exact official and downstream baselines before semantic adoption | Report integrity, Git ancestry, clean-diff gates | `c3303b7cfd` |
| Profile export isolation, unattended approval boundaries, credential digests, scanner and security floors | ADOPTED | Applies official isolation and credential-handling behavior without weakening downstream profile scope | Security, profile, approval, credential and scanner test groups | `0acd63b1e9` |
| Turn liveness and damaged transcript repair | ADOPTED | Restores valid role alternation and preserves resumable conversations | Runtime, session and transcript-repair test groups | `9192c58c6d` |
| Input sanitization, cache stability and compaction | COMPOSED | Combines official sanitization and compaction behavior with downstream cache and Windows execution constraints | Agent compression, tail-budget and runtime qualification tests | `a253afb60a`, `bc07a78c9c`, `4e5fd858ca` |
| Transactional updater lifecycle and Windows watchdog maintenance | COMPOSED | Retains downstream Windows watchdog authority while adopting plan, snapshot, apply, restart, verify and receipt semantics | Windows qualification, updater, watchdog and installer tests | `47ab6f270b`, `ca54ca689c` |
| Hidden Windows console for the Go watchdog | ADOPTED | Uses Windows process creation flags without changing non-Windows behavior | Go test, vet and build; Windows process tests | `c20448608d` |
| Hidden Windows console for A2A helper servers | ADOPTED | Hides helper consoles and preserves server lifecycle behavior | A2A process tests and external Go build verification | `b40ef6a724` |
| Desktop backend recycle and remote recovery | ADOPTED | Adds bounded backend recycle and remote liveness recovery | Desktop backend, remote and lifecycle suites | `60361524a7` |
| Side-question `/btw` flow and planning support | ADOPTED | Adds cache-safe side questions and planning flow to the agent surface | Agent command, planning and conversation tests | `f5056d93f7` |
| ACP agent and provider projection | ADOPTED | Projects provider and agent metadata through ACP without broadening the core tool surface | ACP and ACP adapter suites | `57695e99f1` |
| Official provider catalogue semantics and downstream provider plugins | COMPOSED | Aligns official provider discovery while retaining downstream provider extensions | Provider catalogue, routing and configuration tests | `c2a77968c7` |
| Anthropic adapter architecture | ADOPTED | Moves to the coherent official adapter flow with downstream credential and routing boundaries intact | Anthropic adapter, billing, authority and retry tests | `7a53a5541c` |
| Desktop fleet, provenance, OAuth, consent, preview, model and E2E behavior | ADOPTED | Integrates compatible official Desktop behavior into the downstream Electron application | Desktop Vitest, typecheck, lint and production build | `d3637a93b0`, `9f94056138` |
| CI runtime gates, Node behavior, Telegram lifecycle, process registry and installer safety | COMPOSED | Adopts official gates and preserves stricter Windows identity and process checks | Phase 10 aggregate, PowerShell 7 and Windows PowerShell 5.1 installer tests | `ca54ca689c`, `0b5e008e04` |
| Official semantic version `0.21.0` | ADOPTED | Aligns Python distribution, lockfile, CLI and Desktop package versions to the official release | Version consistency and package metadata checks | `dc0772f946` |
| Windows proxy environment and Desktop query-provider contracts | ADOPTED | Handles Windows case-insensitive environment names and supplies the real query context in preview tests | Targeted proxy and preview-pane suites; full Desktop suite | `9f94056138` |
| Go watchdog as sole outer process authority | DOWNSTREAM_STRONGER | Preserves the downstream single-authority restart and identity model | Watchdog Go and Windows process-registry suites | Existing downstream implementation plus `47ab6f270b` |
| Local Llama, GGUF loading and model hot-swap | DOWNSTREAM_STRONGER | Retains downstream local inference and controlled hot-swap support | Local model, routing and hotswap test groups | Existing downstream implementation |
| Embedding services, Semantic Graph and Ebbinghaus memory | DOWNSTREAM_STRONGER | Keeps downstream memory and retrieval extensions alongside official agent changes | Embedding, semantic graph, Ebbinghaus and memory-provider tests | Existing downstream implementation |
| Downstream provider catalogue extensions | COMPOSED | Keeps additional providers while adopting official catalogue resolution rules | Provider catalogue and fallback tests | Existing downstream implementation plus `c2a77968c7` |
| Tailscale and operator surfaces | ALREADY_PRESENT | Existing downstream operator access remains the authoritative implementation | Operator, remote access and configuration tests | Existing downstream implementation |
| macOS-only TCC behavior | DEFERRED | Not adopted into the Windows target because it has no valid Windows runtime contract | Platform applicability review | N/A |
| Generated output, caches, temporary evidence and developer-machine paths | REJECTED_ARTIFACT | Excluded from source control and removed after qualification | Repository status, tracked-file and local-path scans | N/A |
| Dependency vulnerability review | ADOPTED | npm audit and OSV lockfile scans are release gates for this refresh | npm audit: zero findings; OSV scan of five lockfiles: zero findings | Qualification evidence |

## Qualification evidence

The clean Desktop qualification worktree passed type checking and linting with no errors. Lint retained 224 pre-existing warnings. The complete Desktop Vitest run passed 780 test files with one skipped file; 8,157 tests passed and nine were skipped. The production Desktop build completed and its distribution assertion passed. `npm audit` reported zero vulnerabilities, and OSV Scanner 2.3.8 reported zero findings across the five selected lockfiles.

The Windows Phase 10 aggregate passed 111 tests with 35 skips. Installer tests passed under PowerShell 7 and Windows PowerShell 5.1. The watchdog passed `go test ./...`, `go vet ./...`, and `go build -trimpath`. The native-Windows non-integration Python inventory covered 3,499 files and about 35,807 tests. A checkpointed qualification pass retained prior file-level successes and reran 209 failed or unfinished files: 4,999 assertions passed and 527 failed. The remaining failures are recorded as Windows platform-qualification debt rather than hidden with blanket skips. During this run, a real Python 3.11 runner isolation defect was fixed by launching Windows pytest children with explicit process-group and no-console creation flags; the runner regression suite then passed 9 tests with one skip.

## Operational limits and observations

No production gateway, Desktop backend, watchdog or A2A service was restarted or deployed during qualification. The external A2A helper change remains a separate committed worktree and is not silently deployed by this refresh.

During an early installer-test invocation, the installer script was dot-sourced before its test guard and started two `winget` child processes for FFmpeg. The exact test process trees were stopped. The test guard was then corrected and both PowerShell installer suites passed. No blind uninstall was attempted because the prior machine package state could not be established safely.

The refresh is eligible for a non-force `main` push after final repository gates, a fresh remote ancestry check and a clean integration-worktree check. GitHub CI remains the merge-line authority; any failing workflow must be repaired before the refresh is declared operationally complete.
