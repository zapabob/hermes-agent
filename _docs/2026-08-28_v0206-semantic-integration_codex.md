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
