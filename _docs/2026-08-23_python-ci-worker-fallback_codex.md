# Fork CI Python worker fallback

Date: 2026-08-23

## Scope

The fork runner fallback in `tests.yml` correctly moved the Python suite from the official 96-core runner to `ubuntu-latest`, but the test worker count remained fixed at 96. The exact-SHA main CI run `32584168430` stayed in the Python test step for more than 35 minutes while the other jobs completed; the Windows-only job remained queued independently.

## Change

`HERMES_TEST_WORKERS` now resolves to 96 for `NousResearch/hermes-agent` and 8 for the fork. The official repository path is unchanged, while the fork follows the runner's standard `cpu_count * 2` bounded-parallelism baseline instead of oversubscribing it with the official 96-core value.

## Verification

- Reproduced the stalled state on `390eebb78c75b6a2f6570a0658f8aee8f14de89e` in run `32584168430`.
- Canceled that stale run before publishing the workflow correction.
- The first fresh run used 4 workers and was canceled after confirming it was progressing too conservatively for the full suite.
- A fresh exact-SHA CI run with the 8-worker fork setting is required after commit and push.
- No Hermes runtime process was stopped or restarted for this CI-only correction.

## Follow-up

Confirm the new main CI Python test job completes successfully on the fork standard runner, then confirm the Windows-only job and all required exact-SHA workflows before closeout.
