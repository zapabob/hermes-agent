# PR #70 review against current main

## Verdict

- `codeQualityStatus`: WATCH
- `recommendation`: REQUEST_CHANGES
- Code delta: APPROVE
- Operational merge action: HOLD until the current-main merge result has fresh required checks, including Desktop E2E
- PR head: `e7ba92b5a337b4fe05d51f718dd72f94eb23ad23`
- Current main: `fe6acdca3258dc70b5997a4436a0a172e5e86da9`
- Conflict-free computed merge tree: `74f24f7f389e880ae36b90cb348b77b44e4f1647`

## CRITICAL

None.

## HIGH

### The exact current-main merge result has not passed required cloud CI

PR #70 still reports `UNSTABLE` and its aggregate `All required checks pass` job failed. Those failures are conclusively inherited from its old base rather than introduced by the PR, but they are still not evidence for the exact merge into current main. The PR's added `apps/desktop/e2e/backend-skin-wallpaper.spec.ts` was skipped by Desktop E2E, leaving the real Electron + Python gateway + file-resolution path without cloud-run evidence. Update/rebase the PR onto `fe6acdca...`, run fresh required checks for that exact result, and require Desktop E2E to execute before merge.

This is an operational verification blocker, not a request to alter the PR's production code.

## MEDIUM

### E2E freezes current built-in palette literals

`apps/desktop/e2e/backend-skin-wallpaper.spec.ts` asserts exact built-in values `#0e0e0e` and `#eaeaea`. The behavior contract is that backend wallpaper metadata must not replace the built-in palette; literal colors make the E2E fail on a legitimate future palette refresh. A relation-based assertion against the built-in theme contract would age better. This is non-blocking for correctness now because the literals match current main and the test still catches the intended regression.

## LOW

None.

## Baseline CI attribution

PR run `32361738566` tested a synthetic merge on old base `003d7f9539ba54824e686cae72f7492d6639dced`. Exact-base push run `32329806334` failed the same eleven substantive jobs: Python slices 1, 2, 4, 6, 7 and 11; all three Desktop UI shards; Desktop lint; and tests-js. Failure files and messages match the base run and lie outside this PR, including SCM rail types/i18n, external-link and artifact registry tests, gateway status `posixpath`, disposable Git identity, local-env `path_sep`, missing `sync_memory`, and the stale tests-js allowScripts pin. The PR's directly changed unit/integration tests passed in that run.

## Current-main automatic merge review

- Merge is conflict-free.
- Effective current-main delta is 13 files, 309 insertions and 66 deletions.
- `apps/desktop/src/lib/media.ts` drops from the effective delta because current main already exports `isFileMediaPath`; current main's `isMarkdownDocumentPath` fork feature remains intact.
- The only remaining overlap, `tests/tui_gateway/test_protocol.py`, is a separate additive assertion hunk and retains all current-main protocol coverage.
- Focused Python tests on the computed merge result passed: 77 tests in `tests/hermes_cli/test_skin_engine.py` and `tests/tui_gateway/test_protocol.py`.
- `git diff --check` on the effective merge delta passes.
- No artifact, credential, dependency, workflow, or unrelated file enters the effective delta.

## Semantics and fork preservation

The merge keeps hand-tuned built-in Desktop palettes, typography and terminal settings, adding only backend wallpaper image/fit/position/overlay metadata. It removes stale decoration, avoids duplicate theme entries, resolves user-skin relative paths beside the YAML, retains absolute/URL forms in the Python API, routes filesystem media through the existing authenticated resolver, and intentionally refuses arbitrary renderer HTTP(S) fetches from remotely supplied skin data. The fork's Leva Backdrop controls, readability class, fallback artwork, current-main Markdown preview support, and gateway resolver remain present.

The fork implementation is aligned with open official PR `NousResearch/hermes-agent#90721` while adding fork-specific Backdrop preservation. It does not change core model tools, prompt caching, or configuration API shape.

## Test and maintainability perspective

The `remove-ai-slops`, `programming`, TypeScript, and Python perspectives were applied. Tests exercise behavior across conversion, built-in decoration/removal, registry de-duplication, relative-path resolution, gateway payload and Electron E2E. No assertion weakening, deletion-only test, brittle prompt test, untyped escape hatch, or needless abstraction was found. The fixed palette literals above are the sole change-detector concern.

## Blockers

1. Refresh the PR onto current main and obtain required CI for the exact merge result.
2. Ensure Desktop E2E runs rather than skips and records a passing result for `backend-skin-wallpaper.spec.ts`.
