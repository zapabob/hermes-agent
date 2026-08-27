# Hermes Agent Windows v0.20.6 semantic integration

## Campaign boundary

- Downstream start: `4198d292cc1628383522ec201d4d55002da72f4f`
- Frozen upstream target: `5fc308a70719a83cccdbba4c0e39c23f5a8239d5`
- Merge base: `1fe0f2f3ac9748ce799272eb93bee2937b5ab802`
- Captured at: `2026-08-28T02:33:55+09:00`
- Integration branch: `codex/integrate-upstream-v2026.8.27`
- Isolated worktree: `.worktrees/integrate-upstream-v2026.8.27-20260828`

Commits newer than the frozen upstream target are outside this campaign.
The primary checkout remains untouched.

## Task 1: campaign metadata

The immutable snapshot generator was extended to write the canonical
`.codex/UPSTREAM_SNAPSHOT.json` authority and a report whose filename and
title derive from the explicit capture date. The generator continues to reject
moving upstream refs and does not fetch or mutate Git history.

The generated delta contains 361 upstream commits, 493 touched files, and 96
direct fork intersections. Decisions are 114 `ADOPT`, 202 `COMPOSE`, 22
`DEFER`, and 23 `IGNORE`.

All 299 commits carrying at least one required review category were audited by
decision and category. No security-critical, data-integrity,
credential-boundary, Windows-relevant, gateway-API, or public-API commit is
deferred or ignored. The 22 deferred priority entries are Desktop test,
formatting, or superseded implementation commits, except
`beb212dcc5444f629a84ce0d64ac332f958a0e06`, which is the explicitly deferred
managed-SSH carrier assigned to Task 8.

### TDD evidence

RED:

`HERMES_PYTHON=... bash scripts/run_tests.sh tests/upstream/test_snapshot_sync.py -q`

Result before implementation: 1 failed, 3 passed. The failure was the missing
`.codex/UPSTREAM_SNAPSHOT.json`.

GREEN:

## Task 2: Windows gateway quiesce and process ownership

Composed carriers:

- `03537d69dcbd5d9d5070ce6440fc066958ca398e`
- `790e1eb6bd576261e6b9e70fcfe4fbdf17f866bb`
- `b3e477f304e43b7ff6427c7e186bfd9e524bbff2`
- `de2a9de7889e88ac8bdc025ae1ae48a1d6cac255`
- `5d7ed70eef85ccac8a62cea53806440b2c605163`
- `71823be9daea10a4b9f29f5b995468bae2601b99`
- Final test correction `adb29d8527566c0252d2a402b8bf16c2ec6c575a`

The gateway now accepts a control-socket `pause-for-update` verb and reports
the accepted state, process ID, and drain budget. The updater requests that
verb first, honours the greatest declared drain budget, and retains the
existing planned-stop and force-stop fallback for older gateways.

Windows SCM ownership is established from strict profile PID metadata,
creation times, parent ancestry, a unique service host, and a second identity
read before `sc.exe stop`. The updater stops the service, waits for both SCM
state and the original descendant identities to disappear, and aborts before
installation mutation when ownership is unreadable or ambiguous. Resume and
fleet reconciliation carry verified service/profile outcomes without treating
the bookkeeping token itself as a live runtime.

The later upstream catch-up restart carrier
`8246c4f92ad57c1c0190609e6ad5f524f35729ec` was not adopted here. It adds a
separate updater-owned restart catch-up authority, which conflicts with this
fork's Go-watchdog outer restart invariant. The graceful core drain and bounded
transaction remain composed with the existing planned-stop handshake.

### TDD evidence

RED observations included the missing pause client, 25 SCM/ownership failures,
3 restart-reconciliation failures, one recycled-PID false stale row, and four
resume-token false-positive fleet expectations.

GREEN focused lanes:

- Control-socket pause: 3 passed, 2 skipped on native Windows transport.
- SCM pause, ownership, cold-start, reconciliation: 96 passed, 7 skipped.
- Strict gateway identity: 76 passed.
- Windows restart reconciliation: 4 passed.
- PID reuse: 6 passed.
- Resume-token fleet semantics: 17 passed.

Combined Task 2 lane: 194 passed, 7 skipped, including two native Windows
named-pipe control-socket tests.

## Task 3: Windows real-profile browser contract

Composed the production browser sequence from `830e4a29be7571860c60d40411e0c8f42511c34d`
through the final carriers `f1d05ce7d84f04fd2304be604ba3e8ad69dad47b`,
`931bf613b12e82a0c1ae6d016ef22651ba7291cd`, and
`e4451ec6e5923e35dde75aabcb14944b1f15c16a`. Branch-only Windows proof
workflow and live-test artifacts were intentionally excluded.

The snapshot now fails immediately with a recognizable locked-profile state and
never terminates the user's browser. The autoclose setting only arms an offer;
the destructive close remains an explicit CLI action after user approval.
Executable names and `--user-data-dir` bindings are exact, malformed or
unreadable identity fails closed, and release is re-probed before a retry.

The copied authentication store is secured through the canonical directory
helper, excluded from backup/import, and denied to generic file reads. Stable
browser identity is kept separate from unsupported Beta, Dev, Canary, and
ambiguous channels.

Windows-specific integration refinements preserve `HOME` semantics when testing
POSIX targets, make the synthetic lock fixture work without symlink privileges,
and force UTF-8 decoding for helper subprocesses.

Verification:

- Browser profile, resolver, routing, timeout, and credential guards: 143 passed.
- Hardened exact/ambiguous close behavior is included in the 75-test profile lane.
- Ruff and Python byte compilation passed for all changed Python files.
- Desktop renderer typecheck and ESLint passed.
- Isolated `python -m hermes_cli browser --help` exposed only the explicit
  `close-profile` action and its destructive approval warning.

## Task 4: MCP stdio aggregate liveness

Composed `98fce8e52d612d9bc7e873db40a7810b534b6f8e` and
`ef46ec03e11452eab74e261147668fb64a3d9fd3` without adding another lifecycle
manager. The watcher now reports all-dead only when every tracked stdio PID is
confirmed absent through `psutil.pid_exists()`.

A live sibling keeps the watcher pending. Missing PIDs, HTTP transports, missing
`psutil`, and probe exceptions remain unknown and therefore fail open with
respect to liveness.

Verification: 8 focused tests passed; Ruff and Python byte compilation passed.

## Task 5: bounded session durability and stdout READY

Composed `6d4e851d80e1dfeea69899c3cbbdf529a92bc255`,
`f2dd32d3e50cf1c90e16f4ef55d41289b1848031`,
`42e1aa39fce37cf3640599ff3e25dd1e2bf18ae4`, and the final review carrier
`8d95ab1b3718fb2f7887eabe3fc6fd1af17bda6b`.

SIGTERM, SIGINT, and atexit paths now prepend a bounded best-effort session
flush with a default five-second budget. The existing idle reaper owns
incremental flush cadence and skips active turns. Persistence reuses the
canonical marker-deduplicated session writer.

Machine sentinels for READY and port conflict use fd 1 even when Python stdout
is redirected. Delivery failures never kill an otherwise healthy backend.

Windows validation removes the obsolete POSIX-only skip, invokes the Python
handler directly where `os.kill(SIGTERM)` maps to `TerminateProcess`, and
captures subprocess text explicitly as UTF-8.

Verification: 15 focused tests passed. The real backend E2E kept stdout and
stderr separate, observed `HERMES_BACKEND_READY` on stdout, connected to the
announced listener, and completed well below the Desktop 90-second timeout.
Ruff and Python byte compilation passed.


## Task 6: canonical memory credential persistence

The generic memory-provider setup now delegates credential writes to the
canonical `save_env_value` path rather than editing `.env` independently.
That writer is profile-aware, uses the existing atomic replacement boundary,
and removes NUL plus every `splitlines()` separator before serialization.

Invalid or denylisted keys are rejected independently, so one rejected entry
does not discard unrelated valid credentials. Filesystem failures remain
visible to the caller instead of being converted into a successful setup.

Verification:

- Memory setup and writer boundary: 25 passed, 1 POSIX-only skip.
- Canonical config, export, and managed-scope lanes: 82 passed.
- Combined Task 6 rerun: 103 passed, 1 skipped.
- Ruff, Python byte compilation, and staged diff checks passed.

Commit: `804cfd2a78979d9ea6e3957db867654278af20ef`.

## Task 7: session ownership and Desktop runtime resilience

This task composes the upstream session-owner campaign without reviving the
removed dispatcher architecture or importing the later managed-SSH and
power-resume campaigns.

Legacy sessions can be backfilled with an exact owner. Remote session creation
stamps that owner once, owner lookup spans all loaded session slices, and
registry topology accepts only exact owner routes. Unowned historical
transcripts remain available through a read-only recovery path; send and
interrupt operations stay blocked until a live owned runtime is available.

Transcript tails are scoped by owner profile and connection. Deletion removes
all matching owner scopes and purges the legacy unscoped entry. Backend
keepalive freshness tolerates the documented delayed interval. Renderer reloads
are bounded and an escaped visible error page replaces silent load failure.
The headless root exposes the loopback token only on its gated loopback route.

Finally, a main-process dial claim serializes backend ownership by
`(connectionId, profile)`. Renderer connection IPC, terminal, media, registry
dispatch, roster enumeration, and connection-wide update entry points share the
same in-flight dial instead of creating duplicate local or SSH backends.

Verification:

- Legacy session-owner backfill: 18 passed.
- Remote owner stamp: 1 passed; renderer ESLint and TypeScript passed.
- Owner lookup across slices: 85 passed; renderer ESLint and TypeScript passed.
- Registry owner topology: 49 passed; renderer ESLint and TypeScript passed.
- Read-only transcript recovery: 93 passed; renderer ESLint and TypeScript passed.
- Owner-scoped transcript tails: 95 passed.
- Delayed keepalive policy: 9 passed; Electron ESLint and TypeScript passed.
- Bounded renderer lifecycle: 29 passed; Electron ESLint and TypeScript passed.
- Gated headless root: 5 passed; Ruff and Python byte compilation passed.
- Backend dial claim and registry lane: 95 passed; Electron ESLint and
  TypeScript passed.

Commits:

- `8c5eaa01bb20ceb61c8e9c3cc4c690b872bb3f7a`
- `1bbcd1b8b392ed3503942f90d97fa247c790b64c`
- `dc1761ba87b410f84f3d3f4ff9aa6cb21652cfd6`
- `959fa5979fc417db3998ded8ec7350c26b1eacd3`
- `7577e232b5c2311d8e4fc6368854a43ac63a279b`
- `315f4d01b30f6a399064bc260526f81b46a4b25a`
- `f61a1f4f5698d68f91a6a710e422f0b2c8ba083c`
- `8519d4c8d973499ae0b60effa34014e5e3f6615e`
- `8b50fdc3fef65626337ccd2d4a3f2aa44a8d0ab8`
- `f9e942c962d6056b3c94edfcdf1a59a5142b97e7`

The broader Desktop `session-tile-actions.test.ts` lane still contains an
existing `submitText` recovery failure. Reverting the ownership change did not
alter that failure, so it is recorded as pre-existing rather than hidden or
rewritten during this task.


## Task 8: transactional managed SSH updates

Composed the backend engine and wiring carriers
`6170fff19cd622422dd745819cc96f2e6d13f21e`,
`65335549a6321811fc11fa4084d0af986590eaff`,
`0cefc491c8f3e3d84fd69f4a9bc6f85b8d16556a`, and the final spawn correction
`beb212dcc5444f629a84ce0d64ac332f958a0e06`. The per-connection renderer
surface comes from `bc4eea77739c5e531b2a879e43e3b51f135fd74f`.

Each managed SSH update claims the connection, journals recovery ownership,
re-proves the remote process identity at termination, observes the remote
update marker and correlated receipt, drains every captured scope, and fences
publication of the replacement backend until rollback can no longer expose a
half-updated connection. The managed lifecycle remains independent of the
local Go watchdog.

Native Windows qualification also executes the generated POSIX launcher under
Git Bash. The two tests that execute the POSIX Python observer are skipped on
native Windows because the host has no POSIX Python path/runtime; command
generation and result parsing remain covered, and the remote-Windows launcher
and observer contracts run natively.

Verification:

- Transaction, remote lifecycle, Windows remote lifecycle, bootstrap
  coordinator, dial claim, and registry lanes: 225 passed, 4 skipped.
- Managed updates renderer and settings lanes: 12 passed.
- Electron and renderer TypeScript passed.
- ESLint error-only lanes and staged diff checks passed.

Commits:

- `7312b178d0f08734cb7d4e930797aa054c83e91b`
- `573e3bf58497f157484f706e809fc3d374ea1a3e`

## Task 9: browser tool-surface compatibility audit

The complete downstream tree still contains 12 files using `cua_browser_*`,
101 files using `computer_use`, 16 files using `browser_exec`, 6 files using
`browser_route`, and 9 files using `typed_browser`. The retained
`computer_use` skill and system prompt explicitly teach the session-scoped
typed-browser capability contract, while the CUA backend and authorization
tests enforce exact binding, current refs, mutation invalidation, and explicit
permission downgrade behavior.

The OSINT plugin depends on the broader `computer_use` surface for live map and
SPA inspection, although its current playbooks use native actions rather than
calling the namespaced route directly. This is sufficient to reject an
unqualified public-surface deletion during the v0.20.6 campaign.

Decision: retain the existing `COMPOSE` classification for upstream carrier
`f780cb36d883bbe4180c023fefb49fe3337e52bb` and keep the downstream
`cua_browser_*` route until a separate migration proves equivalent session,
authorization, and stale-ref behavior through `browser_exec`.

Verification: the retained route, authorization, CUA 0.9 contract, and OSINT
plugin lanes passed 96 tests. The neighboring `browser_exec` CLI file passed
70 tests but failed 22 POSIX-fixture cases on native Windows and skipped 3;
the failures invoke generated `#!/bin/sh` fixtures as Win32 executables and do
not establish migration parity. No obsolete surface was removed.

## Task 10: frozen boundary and release qualification

The campaign remains pinned to upstream
`5fc308a70719a83cccdbba4c0e39c23f5a8239d5`. The snapshot authority records
that exact SHA, the downstream start, and the merge base. Carry metrics and
downstream policy validation are current. No post-v0.20.6 upstream carrier was
added after the freeze commit.

The following post-target themes remain candidates for a separate campaign:
state database synchronous configuration, later MCP reconnect/liveness
follow-ups, post-release updater overlay safeguards, and later cron/process
fixes. The browser surface reduction carrier
`f780cb36d883bbe4180c023fefb49fe3337e52bb` is also intentionally deferred
until downstream browser migration parity is proven.

### Cold-resume correction found during surface qualification

The real Electron recovery lane first exposed an isolated E2E profile that
lacked the locked Python dependencies. After the worktree-local environment
was synchronized, the test revealed a production defect: a newly resolved
session could be inserted after renderer reload from the detail endpoint
without the derived `preview` and `last_active` fields, causing its sidebar
entry to render as `Untitled session`.

The session-detail route now resolves the canonical rich row used by the
sidebar. A route-level regression test proves the preview contract, and the
image-attachment cold-resume E2E disables asynchronous title generation so it
deterministically exercises that preview fallback. The correction is commit
`e0fbbeacce5ffa997057891a28370cf3e62d40d2`.

### Local qualification candidate

Implementation and local surface qualification were completed at
`268d5acedc5a96efba0c6be805bb92d1dac32a7e`. The final receipt-only commit and
its exact GitHub Actions runs are recorded in the publication closeout below.

Exact commands and observed results:

```text
./.venv/Scripts/python.exe -m compileall -q agent gateway hermes_cli tools tui_gateway downstream
PASS

./.venv/Scripts/python.exe scripts/downstream/carry_metrics.py --check
PASS: Carry metrics are current.

./.venv/Scripts/python.exe scripts/downstream/validate_policy.py
PASS: Downstream policy validation passed.

./.venv/Scripts/python.exe -m pytest tests/hermes_cli/test_web_server.py -q
PASS: 169 passed, 5 skipped

npm --workspace apps/desktop run typecheck
PASS

npm --workspace apps/desktop run lint
PASS: 0 errors; 235 pre-existing warnings

npm --workspace apps/desktop run test:unit
PASS: 759 files passed, 1 skipped; 7981 tests passed, 9 skipped

npm --workspace apps/desktop run build
PASS: clean build stamp 268d5acedc5a

npx playwright test e2e/image-attachment-resume.spec.ts --reporter=list
PASS: 1 passed

npx playwright test e2e/boot.spec.ts e2e/boot-failure.spec.ts e2e/image-attachment-resume.spec.ts e2e/unread-dot-restart.spec.ts --reporter=list
PASS: 9 passed

uv lock --check
PASS

uv export --frozen --all-extras --no-dev --no-emit-project --no-header --output-file <temporary-file>
uvx --from pip-audit==2.10.1 pip-audit --require-hashes --disable-pip --requirement <temporary-file>
PASS: No known vulnerabilities found

npm audit --omit=dev --audit-level=high
PASS: 0 vulnerabilities

cd scripts/windows/watchdog-go && go mod verify
PASS

cd scripts/windows/watchdog-go && go vet ./...
PASS

cd scripts/windows/watchdog-go && go test ./...
PASS

cd scripts/windows/watchdog-go && go build -trimpath -o hermes-watchdog.exe .
PASS; generated qualification binary removed
```

The combined changed-Python lanes passed 541 tests with 12 skips. The
downstream/upstream contract lanes passed 488 tests with 3 skips. Full-repo
Ruff passed with one existing invalid-`noqa` warning. Changed-file Ruff and
Python byte compilation passed.

### Windows surface evidence

The Electron recovery suite drove actual app windows and observed normal boot,
backend-ready handshake, dead-backend recovery UI, preload bridge readiness,
persisted image conversation first-open and cold-reload behavior, Desktop
relaunch, unread-state survival across restart, and durable unread clearing.
The focused process, updater, browser, MCP, persistence, profile-ownership, and
managed-SSH lanes cover gateway-already-running, mid-turn drain, SCM ownership,
watchdog planned-stop behavior, PID reuse, sleep/resume keepalive tolerance,
network interruption/reconnect, update handoff, locked Chrome profiles,
approved close, live/dead stdio children, bounded graceful/forced persistence,
and same-session-id profile isolation. These branches include negative
authority assertions; they are not pass-through smoke checks.

The failed boot screenshot generated during qualification belonged to the
fresh `hermes-e2e-*` profile under the system temporary directory. It did not
read, mutate, or delete the normal Hermes profile. The retained temporary
sandboxes and diagnostic build log created by this campaign were removed by
exact path after the regression was fixed.

### Authority conclusions

- The Go watchdog remains the only outer automatic restart authority.
- Hermes core remains the session, profile, approval, graceful-drain, and
  persistence authority.
- The updater owns only the bounded update transaction and its receipt.
- Windows process termination requires re-proven identity and fails closed on
  ambiguous or unreadable ownership.
- Browser profile release remains an explicit approved action.
- Unknown MCP liveness does not become proof of child death.
- READY remains observable on stdout, independent of redirected Python stdout.
- Credential persistence uses the canonical profile-aware validated writer.

### Publication closeout

- Pull request: pending
- Final downstream receipt SHA: pending
- Native Windows workflow run: pending
- Full repository workflow run: pending
- Exact upstream snapshot SHA:
  `5fc308a70719a83cccdbba4c0e39c23f5a8239d5`
