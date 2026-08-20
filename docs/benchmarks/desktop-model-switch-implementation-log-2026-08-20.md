# Desktop model-selection implementation log — 20 August 2026

This is the durable implementation record for the Desktop model-selection
consistency and latency work delivered to `zapabob/hermes-agent`.

## Request and invariants

The request was to investigate the case where the Desktop model shown to the
user differs from the model used for inference, measure the selection delay,
implement a non-duplicative remedy, and provide statistical evidence,
regression coverage, and a real Electron end-to-end check.

The following boundaries were kept throughout the work: the active primary
checkout and its unrelated dirty state were not normalised; the running Hermes
services were not restarted; the upstream PR branch was retained; no user
secrets, local caches, generated runtime state, or unrelated files were staged;
and the fork branch was based on the fork's own `main` rather than on an
unrelated upstream history.

## Investigation record

The symptom was traced to the Desktop model-control path and the gateway's
`config.set` handling. A selected model could be painted before the backend had
acknowledged the selection. In a running session, the old path also deferred a
selection without performing the same selection guards used by the immediate
path. The result was a visible model that could diverge from the model carried
into the next inference request, as well as a redundant live `/models` probe
after the picker had already received the server's catalogue.

The fork and upstream histories were not interchangeable: the fork had a
different `main` with substantial additional commits. A direct branch comparison
would have included unrelated files, so the focused upstream fix was cherry-picked
onto a clean fork worktree. The only conflict was the Desktop E2E fixture; the
fork's process-environment and Electron cleanup behaviour was preserved while
retaining the new fixture capabilities.

## Implementation record

The implementation is carried by upstream-reviewed commit
`01839feb5ccdad6273ceb384960d348792571619`:

`hermes_cli/model_switch.py` accepts a server-owned catalogue proof, avoiding
only the redundant validation request while retaining credential, routing,
normalisation, and runtime construction checks.

`tui_gateway/methods_complete.py` records the exact provider/model pairs served
by `model.options`, including provider aliases.

`tui_gateway/server.py` validates the proof with a bounded five-minute TTL,
prepares guarded running-session selections before deferring them, and carries
the proof into the queued application path.

`apps/desktop/src/app/session/hooks/use-model-controls.ts` acknowledges the
backend result before updating the renderer-visible model state.

The fork-specific E2E readiness synchronisation was added in
`07632e6cd6`: the test waits for the visible `Gateway ready` status in the
fork's split-pane layout before opening the model picker. The handover document
was added in `c7fbde199d`.

## Measurement record

The benchmark used five cross-validation folds with twelve paired observations
per fold, for 60 paired observations. The before and after samples used the same
selection action and recorded the validation-request count as well as elapsed
time.

The before mean was 142.028323 ms (standard deviation 30.974706 ms, median
138.708200 ms, p95 191.891970 ms, 95% CI [134.763858, 150.272002] ms). The
after mean was 5.361253 ms (standard deviation 5.435042 ms, median 3.642400 ms,
p95 15.503510 ms, 95% CI [4.182480, 6.887777] ms).

The paired reduction was 136.667070 ms, with a 95% CI of
[129.077477, 145.142933] ms. The reduction was 96.2252%, equivalent to a
26.4916-fold improvement. Every paired difference was positive. The exact
two-sided sign-test p-value was `1.734723475976807e-18`. Redundant validation
requests fell from 60 to zero.

Raw CSV samples, the JSON summary, the error-bar SVG, and the reproducible
benchmark script are stored under `docs/benchmarks/` and `scripts/`.

## Verification record

The following local gates passed on the fork worktree: seven targeted Python
regression tests, Ruff on changed Python files and tests, 24 Desktop hook
Vitest tests, all three configured TypeScript projects, targeted ESLint with
zero errors, and the Desktop production build including its post-build stamp
assertion.

The real Electron Playwright test reached `Gateway ready`, opened the model
picker, and then reproduced a separate fork-side catalogue-loading problem:
the menu remained in its loading skeleton and `Mock Model Alt` was not served
within 30 seconds. This gate is intentionally recorded as failed, not inferred
to have passed. The next investigation target is the fork's `model.options`
response path and its provider catalogue construction.

The E2E run used `H:\\codex-temp\\hermes-fork-model-switch-20260820` for temporary
files and npm cache because the system C: volume had no usable free space. No
broad cleanup or user-data deletion was performed.

## Publication and merge record

The fork PR was [zapabob/hermes-agent#71](https://github.com/zapabob/hermes-agent/pull/71),
created from `codex/fork-desktop-model-selection-20260820` at head
`c7fbde199df69859537be5e3ae8edc5442386c65`.

GitHub reports the PR as merged. The resulting fork `main` commit is
`e61e7d1909ffdbe242a7e57e4b9b888b54c0d768`. The source branch was deliberately
left available, and upstream PR [NousResearch/hermes-agent#90796](https://github.com/NousResearch/hermes-agent/pull/90796)
remains open at head `01839feb5ccdad6273ceb384960d348792571619`.

At the moment of merge, the fork's Nix check was still running. GitHub accepted
the merge while that check was pending; therefore this log does not describe
the fork as having all CI green. Post-merge runs for the exact merge SHA showed
the Docker workflow successful, with Nix, CI, and auto-fix lint still in
progress or queued at the last observation.

## Follow-up

The remaining engineering task is to reproduce the fork-side `model.options`
loading state with gateway and provider request evidence, then add the smallest
fix that makes the real Electron E2E pass. After that fix, rerun the targeted
regressions, rebuild Desktop, rerun Playwright, and verify post-merge CI by the
exact resulting SHA. Do not convert the current E2E failure or pending CI into a
green claim.
