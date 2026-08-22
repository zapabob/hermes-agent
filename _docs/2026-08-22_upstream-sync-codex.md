# Official upstream synchronisation — 2026-08-22

## Scope

This candidate synchronises the fork with `upstream/main` while preserving
fork-owned behaviour only where the merge policy identifies a genuine fork
surface. The canonical `main` worktree was dirty before this work and was not
stashed, cleaned, or modified.

Source repository: `https://github.com/NousResearch/hermes-agent.git`
Source ref: `upstream/main`
Source SHA: `0012dd1e0c7efc7e86fa75b89567a492057f0c02`
Fork base SHA: `89351922196e2c698ef7fac73d55317e9ed94da0`
Candidate branch: `codex/upstream-sync-20260822-final`

## Procedure

The repository-native `scripts/sync_all.py` was used with
`--dry-run`, followed by the explicit merge mode with
`--allow-preflight-blockers --skip-fetch --conflict-policy official-first`.
The policy file was extended to retire the stale fork-only shell-handoff test
because official Bot Mode now resolves mentions through `message_agent` and
does not generate a shell command. No wallpaper files were part of the sync
diff; the existing wallpaper implementation remains unchanged.

The candidate was re-fetched and refreshed after upstream advanced. The latest
sync report classified 38 upstream paths and 2,376 custom baseline paths:
2,296 preserve-custom, 93 upstream, 2 official-with-overlay, and 10
manual-api-followup paths. The refreshed merge completed with no unresolved
conflicts; the 10 manual paths remain recorded in the generated sync report
for future API-specific review.

The refreshed overlay exposed a malformed subprocess-lifecycle splice in
`scripts/run_tests_parallel.py`; the candidate restores the official
`try`/communication/cleanup structure before promotion. Windows `pywinpty`
cannot represent surrogateescape code points, so `tools/process_registry.py`
now rejects those values before the native call and the regression test checks
that boundary while preserving the POSIX byte round-trip.

## Verification

Passed: staged `git diff --check`; `ruff check` on all staged Python files;
Python `compileall`; model metadata tests (93); state durability and live
writer guard tests (6); browser extension router tests (17); router wiring
tests (3); browser-control broker hardening tests (20); and the selected
Bot Mode Node tests (36). The refreshed update/diagnostics test group reached
66 passes before the Windows PTY boundary was repaired; the focused PTY
regression passes after that repair. Compile emitted only the existing
`update_cmd.py` invalid-escape warning.

The Codex auxiliary total-timeout boundary test remains an environment/base
failure: it reproduced on the pre-sync `main` checkout with the same assertion
and is not caused by the upstream merge. The full backup file run also has an
existing direct-run fixture teardown issue when its global monotonic clock
mock is used without the repository runner environment; the relevant state
durability tests pass with `PYTHONUTF8=1` and `TZ=UTC`.

Desktop TypeScript/build verification was not run. The candidate has no
installed Node dependencies; `npm ci` rejected the existing lockfile/package
drift, and a lockfile-preserving install stopped with `ENOSPC`. No lockfile or
dependency manifest was changed by that attempt.

## Handoff boundary

The refreshed candidate is ready for the explicitly requested commit and push. The
canonical `main` worktree still contains unrelated user changes and generated
`.omo/evidence` files; those paths remain outside this commit and will be
restored unchanged when the local checkout is promoted.
