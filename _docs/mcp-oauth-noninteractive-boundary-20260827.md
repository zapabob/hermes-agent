# MCP OAuth Noninteractive Boundary Closeout

Date: 2026-08-27 JST
Base `main` SHA: `bf6ed46eca4fa57f18cdc874dbd15c3684ee3cfc`

## Summary

Automatic MCP discovery, health probes, and lifecycle reconnects are now
noninteractive. They do not open a browser or prompt on stdin. Browser-based
OAuth remains available only when the user explicitly invokes `/auth` or
`hermes mcp login`.

Unauthorized servers remain parked in the active profile's MCP lifecycle and
may be retried without browser interaction. An explicit authorization context
is valid only for the initial connection attempt; later reconnects suppress
interaction even when the long-lived task inherited the original context.

## Changed

- `tools/mcp_oauth.py`: added an interaction guard that preserves only an
  explicitly forced authorization context.
- `tools/mcp_tool.py`: limited explicit interaction to the initial lifecycle
  connection and suppressed all automatic reconnect attempts.
- `tools/mcp_tool.py`: reused the inspected stdio watcher coroutine instead of
  creating and leaking a second coroutine.
- `tests/tools/test_mcp_tool.py`: added automatic-versus-explicit OAuth boundary
  coverage, reconnect coverage, and an unawaited-coroutine regression guard.
- `tests/tools/test_mcp_tool.py`: normalized Windows environment-variable keys
  for the `ProgramFiles` family because native Windows treats them
  case-insensitively and may expose them in uppercase.

## Verification

- `./scripts/run_tests.sh tests/tools/test_mcp_tool.py -q`: 100 passed, 0 failed.
- Surrounding OAuth, Dashboard, login, startup, cron, and TUI tests: 74 passed,
  1 skipped.
- Explicit browser-boundary test: 1 passed; the mocked browser was called once
  only for the explicit authorization path.
- `python -m ruff check tools/mcp_oauth.py tools/mcp_tool.py tests/tools/test_mcp_tool.py`:
  passed.
- `git diff --check`: passed.
- No `_watch_stdio_children was never awaited` warning remained.

The first main-worktree run of the surrounding suite had one load-sensitive
startup timing failure (`0.344s` against a `0.2s` limit). The same test passed
when rerun alone, and the complete surrounding suite then passed on rerun.
The isolated same-SHA worktree run had already passed the complete suite.

## Known Limits

- The browser-boundary observation used a mocked authorization URL and browser;
  no third-party credentials or live OAuth grant were used.
- The packaged Desktop built from `bf6ed46eca` is not rebuilt by this commit.
  A later Desktop release must rebuild and re-run exact-SHA runtime checks before
  claiming that the packaged executable contains this change.
