# Windows Semantic Refactor — implementation log

- Date: 2026-09-06
- Implementer: Cursor
- Branch: `integration/refactor-win-semantics/e2075ae9f908-20260906-181244`
- Isolation candidate: `...\hermes-refactor-e2075ae9f908-20260906-181244\candidate`
- BASE_SHA: `e2075ae9f9088eb63ccfae2d9927d9f5831cce90`
- Gate: **semantic equivalence** (not line-count reduction)

## Overview

Local-only refactor campaign: freeze Windows contracts with characterization tests, DRY only when CodeGraph + fixtures prove identical semantics, extract cohesive dashboard managed-files helpers (LF-COND-2). No push/PR. Original dirty `hermes-agent` checkout untouched.

## Local commits (logical grain)

| SHA | Why |
|---|---|
| `c8c4aebb35` | Characterize `replace_with_retry` before any FS helper edits |
| `eefaca6077` | LF-COND-2: extract managed-files policy; re-export from `web_server` |
| `986ca16512` | Add `translate_msys_drive_path` core without changing call sites |
| `dfce6a857a` | Delegate `local._msys_to_windows_path` only |
| `875aa025d0` | Delegate `cli._normalize_git_bash_path` only (bare-drive no-ops kept) |
| `e6226f6185` | Freeze MSYS core + wrapper divergence contracts |

## CodeGraph (prepared intelligence only)

| Symbol | Impact | Decision |
|---|---:|---|
| `translate_msys_drive_path` | 25 | Shared core; wrappers thin |
| `replace_with_retry` | 12 | Char tests only; no merge with `atomic_replace` (785) |
| `windows_hide_flags` | 641 | Wave2 OUT_OF_SCOPE |
| `ManagedFilesPolicy` | 3 | LF-COND-2 extract |
| `_setup_worktree` | 25 | LF-COND-1 deferred (cli + `_active_worktree` state) |
| `kanban_home` | 70 | LF-COND-4 deferred (wide monkeypatch surface) |

## Verification (observed)

- `test_web_server_fs.py` + `test_web_server_files.py`: **18 passed** (pre/post LF-COND-2)
- MSYS path contracts + local/git-bash suites: focused runs green on candidate Windows host
- Full Tier-1 / Desktop / Go watchdog / remote CI: **NOT_RUN** (out of this unit scope; push forbidden)

## Explicit non-changes

- Wave4: zero core extracts from `cli.py` / `run_agent.py` / `gateway/run.py` by size
- No `atomic_replace` ↔ `replace_with_retry` unification
- No hide/creation/detach flags unification
- No `normalize_windows_path` ↔ `install_repair._normalize_windows_path` merge
- No kill_process_tree re-unification
- Line-count-only god-file splits refused

## Next safe / stop decisions

1. **Done this follow-up:** adjacent MSYS local-env regression cases (test-only) if still missing `/mnt`/`/cygdrive` in `test_local_env_windows_msys.py`
2. **Stop extracts:** LF-COND-1 (cli worktree) and LF-COND-4 (kanban paths) until re-export + state/monkeypatch identity plans are written and char-gated
3. **LF-COND-3:** only if a pure sibling chunk is identified without SessionDB method coupling — not claimed this turn

## Residual risk

- `_docs/` is gitignored; force-add used only when operator requests ledger commits on this isolation branch
- Finite tests ≠ math equivalence proof
- `windows_hide_flags` blast remains large; Wave2 must stay call-site classified
