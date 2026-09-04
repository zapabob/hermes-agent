# Hermes Agent Windows — Current Upstream Native Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:using-git-worktrees` before editing. Then use `superpowers:subagent-driven-development` or `superpowers:executing-plans`. Every behavioral change follows TDD and `verification-before-completion`.

## Goal

Integrate the compatible architecture, security, state-integrity, MCP, multi-agent scalability, IDE/LSP, Desktop and runtime improvements from `NousResearch/hermes-agent` into `zapabob/hermes-agent-windows`.

The resulting downstream must remain:

**Windows Native Tier-1 / Ubuntu-compatible core**

while preserving every verified downstream capability.

## Immutable inputs

Current downstream frozen upstream:

```text
5a8e8a6b87487c0e0785cd9eb561cc6a96c64f5e
```

New immutable upstream target:

```text
63279301bcbdc185c1b07b98a9312eb0c862f26d
```

Semantic integration range:

```text
5a8e8a6b87487c0e0785cd9eb561cc6a96c64f5e
..
63279301bcbdc185c1b07b98a9312eb0c862f26d
```

Expected upstream delta:

```text
796 commits
```

Do not use:

```text
upstream/main
HEAD
latest
origin/main as the upstream source
a subsequently-created release tag
```

after the campaign begins.

`632793...` is the only permitted upstream source for this campaign.

Re-read downstream `origin/main` when execution begins. Do not assume the downstream start SHA written in this plan remains current.

---

# Model routing

## Daybreak Blue

If approved Daybreak Blue access is available, use:

```bash
codex -m gpt-daybreak-blue-latest
```

for the following classes of work:

```text
GitSpawn / Git trust boundary
credential and OAuth boundaries
profile-secret isolation
MCP security-preflight ordering
process identity and parent-death semantics
gateway liveness authority
SQLite restore / destructive state operations
Windows update / recovery authority
final adversarial security review
```

For these tasks, Daybreak Blue is not merely a code generator.

It must perform:

```text
implementation
→ regression reproduction
→ negative-authority tests
→ race/failure injection
→ mutation/sabotage verification
→ security review of its own patch
```

## Standard Codex / GPT-5.6 Sol

Use normal Codex for:

```text
periodic scheduler
HTTP connection-pool sharing
GC / weakref lifecycle cleanup
LSP multi-root support
FTS storage optimization
Desktop resource limits
general upstream reconciliation
UI
documentation
non-security refactoring
```

If Daybreak Blue access is unavailable, do not block the campaign.

Use normal Codex/GPT-5.6 Sol plus a separate Codex Security review for the Blue-designated tasks.

---

# Global authority invariants

These are non-negotiable.

```text
Windows 11 native remains Tier-1.

Ubuntu core compatibility must remain functional.

scripts/windows/watchdog-go is the ONLY outer automatic restart authority.

Hermes core remains the sole authority for:
- session
- profile
- approval
- gateway ownership
- model catalogue
- tool registry

Do not create parallel authorities.

Unknown liveness is not proof of death.

Unknown process identity is not authority to kill.

PID alone is not process identity.

A process identity check that can race PID reuse must revalidate at the destructive boundary.

Profile scope must survive thread/process boundaries deliberately.

Credentials must never become process-global merely to work around profile scoping.

Prompt-cache prefix behavior must not regress.

Message-role alternation must not regress.

State mutation must be deterministic, auditable and recoverable.

Windows-specific implementation belongs under existing Windows/downstream seams whenever possible.

Official Hermes public APIs remain the preferred integration boundary.
```

Existing downstream features must remain intact:

```text
Go watchdog
llama.cpp/GGUF runtime
llama hot-swap/hot-standby
local embedding recovery
Semantic Graph
Ebbinghaus memory
local secretary
Hypura
provider fallback rotation
Irodori / VOICEVOX
VRChat autonomy
Unity/VRChat bridge
AITuber
OSINT integrations
Desktop Git CRUD/review/tree
watchdog-managed Desktop backend
Security Center/hardening
```

---

# Mainline policy

Do not develop directly in `main`.

Use:

```text
isolated worktree
→ RED regression
→ minimum semantic implementation
→ focused GREEN
→ neighbouring suite GREEN
→ one logical commit
→ record exact SHA
→ cherry-pick exact SHA into main
→ verify exact main HEAD
→ push main
→ inspect CI
→ continue
```

`main` must remain bisectable.

Forbidden:

```text
WIP commits on main
blind merge upstream/main
blind cherry-pick of a commit range
one 796-commit integration commit
final squash
fixup commits left in main
unrelated refactoring inside P0 patches
ours/theirs conflict resolution without semantic review
```

Each logical commit must be independently revertible whenever possible.

---

# Phase 0 — Freeze the campaign

## Task 0.1 — Create the integration worktree

```bash
git fetch origin

git worktree add ../hermes-agent-windows-632793 \
  -b integrate/upstream-632793 \
  origin/main

cd ../hermes-agent-windows-632793

git status --short
git rev-parse HEAD
```

Record the actual downstream start SHA.

Do not reset, clean or stash the user's primary checkout.

Ensure both upstream commits exist locally:

```bash
git cat-file -e \
  5a8e8a6b87487c0e0785cd9eb561cc6a96c64f5e^{commit}

git cat-file -e \
  63279301bcbdc185c1b07b98a9312eb0c862f26d^{commit}
```

If the target does not exist, fetch that exact object from NousResearch.

Do not merge `upstream/main`.

---

## Task 0.2 — Generate the immutable report

Run:

```bash
python scripts/upstream/snapshot_sync.py \
  --upstream-sha 63279301bcbdc185c1b07b98a9312eb0c862f26d \
  --downstream-ref HEAD \
  --base-sha 5a8e8a6b87487c0e0785cd9eb561cc6a96c64f5e \
  --report-only
```

Verify that the tool reports the exact SHA and does not resolve a moving ref.

Review:

```text
SECURITY_CRITICAL
CREDENTIAL_BOUNDARY
DATA_INTEGRITY
WINDOWS_RELEVANT
FEATURE_OVERLAP
GATEWAY_API_CHANGE
DESKTOP_API_CHANGE
PLUGIN_API_CHANGE
PUBLIC_API_CHANGE
```

Do not assume automatically generated `ADOPT`/`COMPOSE` classifications are sufficient semantic review.

---

## Task 0.3 — Archive the old snapshot and open the new one

Use the real current ISO timestamp.

```bash
python scripts/upstream/snapshot_sync.py \
  --upstream-sha 63279301bcbdc185c1b07b98a9312eb0c862f26d \
  --downstream-ref HEAD \
  --base-sha 5a8e8a6b87487c0e0785cd9eb561cc6a96c64f5e \
  --captured-at <CURRENT_ISO_TIMESTAMP> \
  --archive-existing \
  --apply
```

Inspect:

```bash
git diff --check

git diff -- \
  .codex/UPSTREAM_SNAPSHOT.json \
  .codex/UPSTREAM_POLICY.md \
  UPSTREAM_ADOPTION.yaml \
  _docs/upstream-campaigns \
  _docs/upstream-integration-*.md
```

Commit only campaign metadata:

```bash
git add \
  .codex/UPSTREAM_SNAPSHOT.json \
  .codex/UPSTREAM_POLICY.md \
  UPSTREAM_ADOPTION.yaml \
  _docs/upstream-campaigns \
  _docs/upstream-integration-*.md

git commit -m \
  "chore(upstream): freeze current Hermes snapshot 6327930"
```

Run policy checks.

Then cherry-pick this exact logical commit to `main`, verify and push before source integration begins.

---

# Phase 1 — P0 security boundary

## Task 1 — Close the GitSpawn execution class

**Upstream semantic source**

```text
f6234d00c5d59450adea1d7edd30ad3859375c79
```

**MODEL:** Daybreak Blue if available.

The downstream has more Git surfaces than stock Hermes because it exposes Git tree, CRUD, diff, review and worktree operations.

Therefore do not port only the Python upstream patch.

Audit every automatic Git invocation in:

```text
agent/
gateway/
hermes_cli/
tui_gateway/
tools/
apps/desktop/electron/
apps/desktop/src/
downstream/
```

Search:

```bash
git grep -nE \
  'subprocess.*git|Popen.*git|spawn.*git|execFile.*git|exec.*git|git diff|git show|git log|git blame'
```

Every Git operation that may execute before explicit user trust/approval must use the canonical hardened Git environment.

Required contract:

```text
automatic Git probe
→ stdin disabled
→ global/system config ignored where appropriate
→ fsmonitor disabled
→ hooks disabled
→ pager/editor disabled
→ credential-helper execution neutralized
```

Diff-rendering operations additionally require:

```text
--no-ext-diff
--no-textconv
```

for:

```text
diff
show
log
blame
```

Do not add those flags to commands that reject them.

### Critical downstream audit

Explicitly cover Desktop:

```text
git-review-ops
git-ipc
git-worktree-ops
git-ref-ops
git-root
repository-tree context gathering
diff/review pane
```

Do not allow Electron to bypass the hardened Python contract by spawning raw Git independently.

If Desktop must spawn Git itself, provide a single equivalent hardened helper and test it independently.

### Tests

Construct a real malicious repository containing inert test payloads through:

```text
core.fsmonitor
core.hooksPath
diff.<driver>.command
diff.<driver>.textconv
```

Prove:

```text
baseline plain git triggers test payload

Hermes automatic workspace probe does not
Hermes diff does not
Desktop Git tree does not
Desktop review does not
worktree preparation does not
goal/workspace fingerprint does not
```

Mutation test:

remove one of:

```text
noninteractive environment
--no-ext-diff
--no-textconv
```

and prove at least one regression test turns RED.

Logical commit:

```text
security(git): harden all automatic repository probes
```

Integrate to `main`, verify exact HEAD and push before continuing.

---

# Phase 2 — Windows inner liveness without competing restart authority

## Task 2 — Add native Windows loop-scheduling witness

**Upstream source**

```text
d7bda2ad892a596a35c75852356fb5eba17fa1a5
```

**MODEL:** Daybreak Blue.

On POSIX preserve AF_UNIX behavior.

On native Windows use a dynamically assigned:

```text
127.0.0.1:<port>
```

TCP loopback witness owned by the gateway event loop.

Required evidence model:

```text
heartbeat file fresh + loop answers
→ ALIVE

heartbeat stale + loop answers
→ ALIVE / stalled heartbeat writer

heartbeat stale + armed loop silent for sustained strikes
→ WEDGED evidence

witness unavailable / malformed / ambiguous
→ UNKNOWN
```

Never convert UNKNOWN into destructive authority.

The Python/Hermes layer may classify health and exit/request recovery.

It must not create an outer automatic restart loop.

The existing Go watchdog remains the sole restart authority.

### Windows-native test

Use a real Windows runner.

Verify:

```text
TCP witness binds
dynamic port is published
external thread can ping it
alive loop responds
blocked loop fails sustained probe
witness bind failure returns UNKNOWN
no Python restart loop exists
Go watchdog remains outer owner
```

Ubuntu regression:

```text
AF_UNIX witness unchanged
```

Logical commit:

```text
fix(windows): compose gateway loop witness with watchdog authority
```

---

# Phase 3 — Persistent execute_code process ownership

## Task 3 — Bind kernels to exact backend lifetime

**Upstream source**

```text
32d5e9d35753430725e88700532b261cfdfa7151
```

**MODEL:** Daybreak Blue.

Persistent Python kernels must not survive the backend generation that owns them.

On Windows, prefer an exact inherited process object handle rather than PID polling.

Required:

```text
parent process object
→ SYNCHRONIZE handle
→ explicitly inherited by kernel only
→ inheritance removed immediately inside kernel
→ user code / grandchildren never inherit it
→ WaitForSingleObject
→ parent exits
→ kernel exits
```

PID reuse must be irrelevant.

If process-handle setup fails, do not accidentally kill a healthy kernel.

Preserve current fail-safe semantics.

Also inspect upstream follow-ups in the frozen range that generalise the parent-death contract to POSIX and adopt compatible semantics for Ubuntu.

### Tests

Native Windows:

```text
long-running kernel exists
parent killed
exact child identity disappears
PID reuse cannot fool the watcher
handle absent from user environment
handle absent from cell global namespace
child spawned by cell cannot inherit parent handle
```

Ubuntu:

```text
parent death also leaves no persistent orphan kernel
```

Go watchdog:

```text
backend recovery sees no kernel belonging to previous generation
```

Logical commit:

```text
fix(execute-code): bind persistent kernels to backend lifetime
```

---

# Phase 4 — FastAPI / Python event-loop integrity

## Task 4 — Remove blocking credential work from async request paths

**Upstream source**

```text
ff0afff0e4881308ac2d2639bd3cddaf3227a4bc
```

**MODEL:** Daybreak Blue recommended.

Audit async FastAPI/WebSocket endpoints for synchronous:

```text
network I/O
DNS resolution
credential refresh
filesystem sync
subprocess calls
SQLite-heavy operation
```

Credential-pool GET/POST/DELETE must run blocking pool work outside the event-loop thread.

Do not solve this by making credential state process-global.

For raw urllib/Copilot token exchange, impose a real wall-clock cap that also bounds DNS-resolution hangs.

### Non-vacuous event-loop test

Start a ticker coroutine.

Inject a blocking DNS/network operation.

Assert:

```text
credential operation remains pending/timeout bounded
ticker continues advancing
unrelated websocket/RPC remains responsive
```

Run on both:

```text
ubuntu-latest
windows-latest
```

Logical commit:

```text
fix(server): keep credential operations off the event loop
```

---

# Phase 5 — Profile/credential scope across background execution

## Task 5 — Propagate ContextVars deliberately

**Upstream source**

```text
cd7811a7a7c9e820c1c0e6b73d8ca799957b8080
```

**MODEL:** Daybreak Blue.

Hindsight background writer, daemon and prefetch threads must inherit the exact spawning profile context through:

```python
contextvars.copy_context().run(...)
```

Do not add:

```text
global os.environ credential fallback
root-profile fallback
re-read random .env
process-global current profile
```

Then audit downstream-specific background execution:

```text
Semantic Graph
Ebbinghaus
local embeddings
Irodori/VOICEVOX where credential/profile scoped
local secretary
Hypura
OSINT workers
AITuber workers
```

Only propagate context where the child logically belongs to that profile.

Do not copy a context into genuinely process-wide shared infrastructure whose calls already receive per-call scoped context.

### Tests

Create:

```text
root profile
profile A secret
profile B secret
```

Spawn background work from A and B concurrently.

Assert:

```text
A reads only A
B reads only B
unscoped thread fails closed
root never becomes silent fallback
```

Logical commit:

```text
fix(profiles): propagate scoped context into background workers
```

---

# Phase 6 — MCP Windows lifecycle

## Task 6 — Correct npx cache launcher selection

**Upstream source**

```text
1a451bfaeb498aea907c6c4c835fb1d6acea354b
```

**MODEL:** Daybreak Blue recommended because the security-preflight ordering is part of the contract.

Windows npm `.bin` selection must prefer:

```text
<binary>.cmd
<binary>.exe
```

and must never select the extensionless shell script merely because `os.access(X_OK)` returns true.

If a suitable launcher cannot be proven, fall back to `npx`.

On POSIX preserve the extensionless binary path.

Critical ordering:

```text
original npx command
→ OSV/malware preflight
→ only after successful preflight resolve cached binary
→ spawn
```

Never perform the rewrite before malware ecosystem inference.

Tests:

```text
Windows .cmd selected
Windows sh wrapper rejected
.exe fallback
missing launcher → npx
Ubuntu extensionless binary unchanged
npx pkg -y unusual shape remains with npx
OSV check provably precedes cache rewrite
```

Mutation the ordering and prove the structural/security test fails.

Logical commit:

```text
fix(mcp): resolve native Windows npm launchers safely
```

---

# Phase 7 — SQLite destructive-state integrity

## Task 7 — Import state.db without replacing a live database generation

**Upstream source**

```text
d47fe28fc5c703fcc6f32962e2b75e0d815ae300
```

**MODEL:** Daybreak Blue.

A live SQLite database must not be replaced by rename while gateway/Desktop/dashboard connections still hold the old file.

For an existing `.db` target:

```text
stage imported DB
→ fsync staged bytes
→ use existing live-safe page-level restore
→ preserve live file identity
→ converge open connections
→ handle WAL/SHM consistently
```

If the target does not exist:

```text
ordinary atomic publication remains acceptable
```

If live-safe restore cannot be proven:

```text
fail/refuse
preserve original database
surface explicit error
```

Never report silent success.

### Windows-specific validation

Use a real holder connection and NTFS.

Assert:

```text
connection stays open across import
connection sees imported rows afterwards
existing DB identity remains coherent
old/new generations cannot split
failed restore leaves original DB untouched
```

Ubuntu equivalent test must also pass.

If the imported backup drops sessions/messages, emit an explicit before/after count.

Logical commit:

```text
fix(state): restore live SQLite databases without generation split
```

---

# Phase 8 — Multi-agent resource architecture

These are P1, but highly relevant to a 24/7 AI workstation.

Use standard Codex/Sol unless security-sensitive review discovers otherwise.

## Task 8.1 — Shared periodic scheduler

**Source**

```text
561b053f794a1781868bb032029d589c67708119
```

Replace one sleeping OS thread per:

```text
delegate heartbeat
turn liveness polling
turn lease refresh
```

with one process-wide periodic scheduler.

Preserve:

```text
cancel semantics
bounded wait for in-flight callback
callback exception isolation
same timing contract
lease-generation fences
turn-liveness generation fences
```

Do not let one bad callback kill the scheduler.

Commit:

```text
perf(agents): consolidate periodic maintenance timers
```

---

## Task 8.2 — Shared synchronous HTTP transport

**Source**

```text
c3b411dfb77fd8a1bad34fb80d4ef1f0e2b6f38e
```

Share only underlying synchronous `HTTPTransport`/pool infrastructure.

Do not share the logical per-agent `httpx.Client`.

Required invariant:

```text
close child A client
≠
close shared pool used by child B

interrupt child A request
≠
tear down child B stream
```

Use request ownership stamping for in-flight socket targeting.

Do not share async pools across event loops.

Preserve downstream Codex Cloudflare routing.

Commit:

```text
perf(agents): share bounded sync HTTP transport pools
```

---

## Task 8.3 — Release completed subagent heaps

**Source**

```text
c96568f66ca49d27beec4545bee9740b09d64018
```

Do not allow ContextVar snapshots to keep completed child agents alive.

Use weak references where the semantics permit.

On `AIAgent.close()` release transcript shadow state including:

```text
_session_messages
_db_flush_scan_prefix
_streamed_assistant_text_parts
```

without altering the parent-visible delegate result.

Add GC/weakref regression tests.

Commit:

```text
perf(delegation): release completed child agent state
```

---

# Phase 9 — IDE-class LSP resource control

## Task 9 — One Pyright process across worktrees

**Source**

```text
80fae22bf5bd8bcf8f2fc9cbe76e1c603deff338
```

This downstream already exposes Git tree, CRUD, review and worktree functionality.

Therefore worktree fan-out must not spawn one Pyright per tree.

For servers supporting multi-root workspaces:

```text
one server_id
→ one process
→ multiple workspaceFolders
```

Use:

```text
workspace/didChangeWorkspaceFolders
```

Single-root LSP servers retain existing per-root behavior.

### Windows-specific tests

Use paths containing:

```text
drive letter
spaces
mixed separator boundaries
multiple Git worktrees
```

Verify:

```text
one Pyright PID
diagnostics work from every worktree
folder URI is correct
closing one worktree does not kill unrelated diagnostics
```

Ubuntu equivalent test must pass.

Commit:

```text
perf(lsp): share Pyright across Git worktrees
```

---

# Phase 10 — SessionDB / Memory projection policy

## Task 10 — Adopt schema-v30 storage semantics carefully

**Source**

```text
2b55ded1ac5f3b41cdc580974e745631dac1bb53
```

Canonical subagent messages remain durable.

Standard word FTS remains searchable.

Only expensive trigram projection should exclude:

```text
cron
subagent
_delegate_from child sessions
```

as upstream specifies.

Before adopting, audit:

```text
Semantic Graph
Ebbinghaus
session_search
CJK retrieval
downstream hybrid RRF
```

No downstream semantic-memory component may depend implicitly on the trigram shadow table as canonical data.

Required model:

```text
canonical transcript
≠
word-search projection
≠
trigram projection
≠
semantic-vector/graph projection
```

Test:

```text
subagent canonical rows survive
normal word search survives
explicit subagent search survives
CJK fallback works
Semantic Graph ingest remains correct
Ebbinghaus bridge remains correct
migration from previous schema succeeds
```

Commit:

```text
perf(state): bound subagent trigram indexing
```

---

# Phase 11 — Restart-safe cron delivery

## Task 11 — Compose durable cron delivery with the Go watchdog

**Source**

```text
b440a492b35f78e8797d2a301256eaea07ae259d
```

A gateway process is not the durable owner of a scheduled result.

Preserve separation:

```text
execution ledger
delivery ledger
gateway process
```

If delivery remains `pending` and no gateway claimed it:

```text
gateway outage/restart
→ keep pending
→ next gateway may deliver
```

If the operation was mid-send and exact external effect is unknown:

```text
→ UNKNOWN
→ no blind retry
```

Do not turn gateway restart into automatic delivery failure.

Go watchdog remains only process restart authority.

Test with actual gateway termination/restart where possible.

Commit:

```text
fix(cron): preserve pending deliveries across gateway restart
```

---

# Phase 12 — Desktop resource limits

## Task 12 — Compose backend spawn coordinator with watchdog prewarm

**Source**

```text
e924615bb1d3dddddd5f029be865059254cca9b5
```

Downstream already has watchdog-managed backend prewarm.

Therefore do not replace backend ownership.

Integrate only the resource-control property:

```text
starting + running local profile backends <= configured limit
```

Remote backend descriptors consume no local process slot.

A slot is released only after process exit is proven.

If teardown cannot prove exit:

```text
keep slot occupied
surface failure
do not assume process disappeared
```

Revalidate backendPool entry ownership across awaits to prevent stale/evicted entries from spawning zombies.

Tests:

```text
100 concurrent local requests
configured maximum never exceeded
queued cancellation
same-key generation race
timeout
real child process test
failed backend that does not exit keeps slot
watchdog prewarmed primary backend does not become double-owned
```

Commit:

```text
fix(desktop): bound local profile backend spawning
```

---

# Explicit DEFER / separate campaign

## Official managed local llama runtime

Do not simply enable the new upstream local-model manager.

The downstream already owns:

```text
hermes_cli/llama_fallback_runtime.py
Go watchdog process recovery
llama hot-swap
hot-standby
local embeddings
Semantic Graph llama runtime
```

A second independent supervisor could create:

```text
two model-process owners
two restart loops
port conflicts
duplicate downloads
catalogue disagreement
VRAM contention
```

Classify upstream managed-local-model functionality as:

```text
COMPOSE / DEFER_TO_LOCAL_RUNTIME_CAMPAIGN
```

A future dedicated design must decide:

```text
official model catalogue authority
download authority
process owner
health owner
hot-swap authority
watchdog relationship
VRAM policy
embedding coexistence
```

before enabling it by default.

---

## Multi-gateway automatic recovery/failover

Do not adopt any mechanism that turns Hermes core into another outer automatic recovery authority.

Gateway may:

```text
detect
record
request restart
exit
```

Go watchdog owns the restart.

---

## VRChat / Unity

Preserve downstream functionality.

Do not modify it simply because no current upstream equivalent exists.

Run its regression suite after plugin/tool registry changes.

---

## Voice

Preserve:

```text
Irodori
VOICEVOX
local TTS
VRChat voice routes
```

Upstream TTS lease/prewarm improvements may be integrated later as a separate logical commit after the primary campaign is green.

---

## Unrelated providers / cosmetic Desktop changes

Do not enlarge this campaign unless needed to satisfy an official public contract or a dependency of an adopted change.

---

# Phase 13 — Remaining 796-commit reconciliation

After all P0/P1 waves above are green, review the remaining upstream delta systematically.

For every commit:

```text
ADOPT
COMPOSE
ALREADY_PRESENT
DOWNSTREAM_STRONGER
DEFER_PLATFORM
REJECT_GENERATED_ARTIFACT
```

must reflect actual downstream semantics.

Rules:

### ADOPT

Use when upstream behavior has no downstream conflict.

Prefer final upstream implementation at the frozen SHA, not intermediate historical versions.

### COMPOSE

Use when upstream owns the public contract but downstream has verified additional behavior.

Typical areas:

```text
Desktop
Windows process lifecycle
provider routing
local models
memory
voice
browser
Git
terminal environment
watchdog backend
```

### DOWNSTREAM_STRONGER

Use only with code and tests demonstrating the downstream contract is strictly stronger while remaining API-compatible.

### DEFER_PLATFORM

Use only when genuinely irrelevant to Windows/Ubuntu and not part of a shared public contract.

Do not classify a Linux feature as irrelevant merely because Windows is Tier-1.

Ubuntu compatibility is supported.

---

# Cross-platform acceptance

## Ubuntu

Run the normal Python suite on Ubuntu.

At minimum confirm:

```text
agent loop
gateway
MCP
SessionDB
cron
memory provider contracts
tool execution
Git hardening
LSP
provider routing
```

No Windows-only branch may leak into Linux runtime.

Linux-only systemd logic must remain explicitly Linux-gated.

## Native Windows

Native Windows evidence is mandatory for:

```text
Git security boundary
MCP .cmd launcher
gateway TCP loop witness
execute_code parent death
NTFS SQLite restore
Desktop backend lifecycle
Go watchdog
PowerShell/Git Bash boundaries
profile/session persistence
network loss/recovery
sleep/resume where affected
```

Linux emulation is not Windows evidence.

---

# Workstation resource qualification

Add or extend a repeatable resource benchmark.

Measure at:

```text
1 child
4 children
10 children
30 children
```

and:

```text
1 worktree
5 worktrees
10 worktrees
```

Record:

```text
RSS
thread count
process count
open handles/FDs
HTTP transport count
live TLS connections where observable
Pyright process count
Python kernel process count
Desktop backend count
state.db size
FTS size
GPU VRAM if local inference is active
```

The benchmark must not rely on one absolute developer-machine threshold.

Compare before/after under the same machine/environment.

Save evidence separately from ordinary unit-test results.

---

# Security verification

For Daybreak Blue-designated tasks, perform a second review after implementation.

The reviewing pass must try to defeat the patch.

Examples:

```text
malicious .git/config
malicious .gitattributes
PID reuse
profile A/B secret crossover
MCP launcher confusion
preflight-order bypass
state.db live holder
WAL/SHM residue
parent process abrupt death
loop-witness unavailable
event-loop DNS hang
```

For each security invariant require:

```text
positive case succeeds
negative-authority case fails closed
mutation of the fix makes test RED
```

Do not accept “test passes” without proving the dangerous branch was exercised.

---

# Main logical-commit integration procedure

After each completed task:

```bash
git status --short
git diff --check
<focused tests>
<neighbouring tests>
git add <only files belonging to this logical change>
git commit -m "<logical subject>"
git rev-parse HEAD
```

Record the SHA.

Then in a clean main checkout:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git status --short
git cherry-pick <EXACT_LOGICAL_SHA>
```

Re-run the focused test against the exact new `main` HEAD.

Only after GREEN:

```bash
git push origin main
```

Verify:

```bash
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

They must match.

For authority-sensitive P0 changes, inspect resulting CI before adding the next major P0 commit.

If main changed remotely between preparation and integration:

```text
STOP
rebase/revalidate in integration worktree
do not force-push
```

If branch protection is enabled later:

```text
do not bypass it
submit the same logical commit as a focused PR
```

---

# Suggested main history

The final history should resemble:

```text
chore(upstream): freeze current Hermes snapshot 6327930

security(git): harden all automatic repository probes

fix(windows): compose gateway loop witness with watchdog authority

fix(execute-code): bind persistent kernels to backend lifetime

fix(server): keep credential operations off the event loop

fix(profiles): propagate scoped context into background workers

fix(mcp): resolve native Windows npm launchers safely

fix(state): restore live SQLite databases without generation split

perf(agents): consolidate periodic maintenance timers

perf(agents): share bounded sync HTTP transport pools

perf(delegation): release completed child agent state

perf(lsp): share Pyright across Git worktrees

perf(state): bound subagent trigram indexing

fix(cron): preserve pending deliveries across gateway restart

fix(desktop): bound local profile backend spawning

chore(upstream): reconcile remaining 632793 snapshot decisions

test(windows): qualify current upstream workstation contracts

docs(upstream): record 632793 integration receipt
```

Do not squash these into one commit.

---

# Verification order

Run the repository-required order:

```text
1. syntax/import sanity
2. policy validation
3. upstream API contracts
4. downstream feature contracts
5. Windows runtime tests
6. Python lint
7. TypeScript typecheck/lint
8. Desktop tests
9. native Go watchdog tests
10. Linux/Ubuntu regressions
11. security and lockfile checks
12. native Windows CI
13. full required GitHub CI
```

Do not reorder away a failing earlier gate merely because a later suite passes.

---

# Required downstream regression suites

Do not complete the campaign without explicitly covering:

```text
tests/downstream/test_windows_contracts.py

scripts/windows/watchdog-go/*_test.go

tests/hermes_cli/test_llama_fallback_runtime.py
tests/local/test_llama_server_contract.py

Semantic Graph registration/retrieval
Ebbinghaus + Semantic Graph bridge

VRChat autonomy
Unity/VRChat bridge

Irodori
VOICEVOX

Hypura

provider fallback/rotation

Desktop Git review/tree

watchdog backend ownership/prewarm

terminal environment provider bridge

Windows Docker/media path translation

Desktop Browser/file-preview separation

Codex Cloudflare routing
```

---

# No false completion

A verification result may be only:

```text
PASS
FAIL
BLOCKED
NOT_APPLICABLE
```

Never report:

```text
probably passes
expected green
covered indirectly
CI should pass
```

as PASS.

For BLOCKED, record:

```text
exact command
environment
error
what evidence is missing
```

---

# Final immutable integration receipt

Record:

```text
target upstream SHA:
63279301bcbdc185c1b07b98a9312eb0c862f26d

previous frozen SHA:
5a8e8a6b87487c0e0785cd9eb561cc6a96c64f5e

actual downstream campaign-start SHA

final downstream main SHA

logical commit list:
- downstream SHA
- subject
- upstream semantic source SHA(s)
- ADOPT/COMPOSE/etc.
- authority touched
- focused test result
- native Windows evidence
- Ubuntu evidence
- GitHub CI run ID

deferred upstream features

known intentional divergences

Daybreak Blue review results

Go watchdog qualification

full CI qualification
```

Explicitly certify:

```text
No upstream commit newer than
63279301bcbdc185c1b07b98a9312eb0c862f26d
was used as implementation input.
```

If a needed fix is discovered upstream after this SHA:

```text
do not silently cherry-pick it
record DEFER_NEXT_SNAPSHOT
```

If it is a critical security dependency required for correctness:

```text
stop this campaign
freeze a new explicit upstream SHA
regenerate the campaign
```

rather than contaminating the existing immutable input.

---

# Definition of done

The campaign is complete only when:

```text
new snapshot is exact and archived correctly

every upstream commit in the frozen range has an explicit reviewed decision

Git automatic probes cannot execute repo-controlled Git configuration

Windows loop witness works natively

Go watchdog remains sole outer restart authority

persistent Python kernels cannot outlive backend ownership

FastAPI credential operations cannot block the event loop indefinitely

profile secret context survives required worker-thread boundaries

MCP selects valid native Windows launchers

MCP security preflight cannot be bypassed by launcher optimization

SQLite import cannot split live database generations

subagent timer/thread growth is bounded

shared HTTP transport does not break per-agent interrupt ownership

finished child agents release transcript state

Pyright is shared safely across compatible worktrees

state.db indexing remains bounded without breaking downstream memory retrieval

cron pending deliveries survive gateway restart

Desktop backend spawning is bounded

local llama/hot-swap/watchdog authority remains singular

Semantic Graph/Ebbinghaus remain verified

VRChat/Unity remain verified

local TTS remains verified

Ubuntu core tests pass

native Windows qualification passes

Go watchdog tests pass

full required CI passes

main remains bisectable through logical commits

final integration receipt is committed
```

Save this plan as:

```text
docs/superpowers/plans/2026-09-04-hermes-current-upstream-windows-integration.md
```

Then execute it.

Do not stop after writing the plan.

Implement task-by-task, create logical commits, integrate verified commits into `main`, push them, observe required CI and continue until the frozen campaign is complete or an explicit BLOCKED condition is reached.
