# Status bar duration / ctx display (CLI)

**Date:** 2026-04-01  
**Worktree:** main  

## Symptom

- Status line like `⚕ qwen-Hakua-core2:latest │ ctx -- │ [░░░░░░░░░░] -- │ 32s` with **`32s` appearing stuck** (and context bar at `--`).

## Root cause (duration)

- Idle refresh used `_invalidate(min_interval=1.0)`, which **shares** `_last_invalidate` with **all** other repaints (cursor blink, stream flush, interrupt-loop invalidates, etc.).
- When another path invalidated within the last second, the 1s throttle **skipped** the idle repaint, so the compact session duration could **freeze for long stretches** (e.g. stuck at `32s`).

## Fix (`cli.py` → `spinner_loop`)

1. **Idle (no slash command, no agent turn):** once per second, call `self._app.invalidate()` directly and sync `_last_invalidate`, instead of `_invalidate(min_interval=1.0)`.
2. **While `self._agent_running`:** treat like `_command_running` — `_invalidate(min_interval=0.1)` so the status bar keeps up even if other invalidation paths misbehave.

## Note on `ctx --` / `--%`

- `ctx --` means `context_length` is missing in the snapshot (no agent yet, or compressor `context_length` falsy).
- Progress `--` means `context_percent` is unset (same).
- Token counts in the bar come from `context_compressor.last_prompt_tokens` after API `usage`; backends that omit usage may leave **0** tokens until estimates update — separate from the clock freeze.

## Verification

- `py -3 -m pytest tests/test_cli_status_bar.py -q --override-ini="addopts="` → pass.
