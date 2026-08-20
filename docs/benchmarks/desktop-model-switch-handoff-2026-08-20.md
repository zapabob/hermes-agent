# Desktop model-selection handover — 20 August 2026

## Scope

This handover covers the Desktop model-picker mismatch and latency change carried
on `codex/fork-desktop-model-selection-20260820` for `zapabob/hermes-agent`.
The source change is the upstream-reviewed commit `01839feb5ccdad6273ceb384960d348792571619`,
with the fork-specific E2E readiness guard committed as `07632e6cd6`.

The fork branch is intentionally based on `zapabob/hermes-agent` `main`, rather
than replaying the unrelated upstream history. The cherry-pick is therefore a
single focused feature change plus the E2E synchronisation guard.

## Measured result

The benchmark used five cross-validation folds with twelve paired observations
per fold (60 paired observations in total), using the same model-picker actions
before and after the change.

| Measure | Before | After | Paired difference |
| --- | ---: | ---: | ---: |
| Mean latency | 142.028323 ms | 5.361253 ms | 136.667070 ms |
| Standard deviation | 30.974706 ms | 5.435042 ms | — |
| Median | 138.708200 ms | 3.642400 ms | — |
| p95 | 191.891970 ms | 15.503510 ms | — |
| 95% confidence interval | [134.763858, 150.272002] ms | [4.182480, 6.887777] ms | [129.077477, 145.142933] ms |

The observed reduction is 96.2252%, or 26.4916 times faster. All 60 paired
differences were positive. The exact two-sided sign-test p-value is
`1.734723475976807e-18`. Redundant validation requests fell from 60 to zero in
the benchmark run. Raw paired data, JSON statistics, the error-bar SVG, and the
reproducible benchmark script are committed beside this document.

## Code and tests

The change records the server-owned model-options catalogue proof, carries that
proof through the running-session deferral path, and acknowledges the selected
model before the renderer paints it. The relevant files are:

- `hermes_cli/model_switch.py`
- `tui_gateway/methods_complete.py`
- `tui_gateway/server.py`
- `apps/desktop/src/app/session/hooks/use-model-controls.ts`
- `apps/desktop/e2e/model-switch-consistency.spec.ts`

Verified locally on the fork worktree:

- Python targeted regression tests: 7 passed.
- Ruff on changed Python files and tests: passed.
- Desktop hook Vitest: 24 passed.
- Desktop TypeScript type-check: all three configured projects passed.
- Targeted ESLint: 0 errors; 62 existing padding warnings.
- Desktop production build: passed, including the post-build stamp assertion.
- Playwright E2E: currently blocked after the real gateway reports ready; the
  model catalogue remains in a loading state and `Mock Model Alt` is not served
  within 30 seconds. This is recorded as a failing gate, not as a passing test.

The E2E run used `H:\\codex-temp\\hermes-fork-model-switch-20260820` for temporary
files and npm cache because the system C: volume had no usable free space. No
user cleanup or broad deletion was performed.

## PR and merge gate

Push this branch to `zapabob/hermes-agent`, open the PR against `main`, and keep
the branch available after merge so the existing upstream PR remains intact.
Do not merge until the fork's required CI is green on the exact PR head SHA and
the Playwright E2E has either passed or has a documented, reproducible fix.
After merge, verify the fork `main` SHA and its post-merge required checks.

The upstream PR that supplied the reviewed change is
https://github.com/NousResearch/hermes-agent/pull/90796.
