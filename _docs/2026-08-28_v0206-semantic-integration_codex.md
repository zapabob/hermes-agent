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
