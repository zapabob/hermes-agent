# Downstream integration SOP

## Scope

This SOP governs Hermes Agent Windows Workstation Edition. Work occurs in an
isolated integration worktree. User changes in the primary checkout are never
reset, cleaned, stashed, or incorporated implicitly.

## Frozen input

The only permitted upstream input for this campaign is
`1fe0f2f3ac9748ce799272eb93bee2937b5ab802`. Run
`scripts/upstream/snapshot_sync.py --upstream-sha <sha> --downstream-ref <ref>
--report-only` before semantic integration. The helper must not resolve a
moving branch.

## Integration procedure

Read `.codex/UPSTREAM_POLICY.md`, `.codex/FORK_INVARIANTS.md`,
`.codex/WINDOWS_PLATFORM_CONTRACT.md`, `FEATURES.yaml`, and `CARRY.yaml`.
Classify each upstream commit in `UPSTREAM_ADOPTION.yaml`. Prefer official
public contracts, compose proven downstream properties through
`downstream/compat/hermes`, and stop when a feature or security invariant
cannot be determined.

Keep fork-owned behavior under `downstream/`, existing plugin entrypoints, or
`scripts/windows/`. Do not create another session, approval, profile, gateway,
model-catalogue, or tool-registry authority.

## Verification

Run gates in the directive order: syntax/import sanity; policy validation;
upstream API contracts; downstream feature contracts; Windows runtime tests;
Python lint; TypeScript typecheck/lint; Desktop tests; native Go watchdog tests;
Linux regressions; security and lockfile checks; native Windows CI; full
required GitHub CI. Record exact SHAs and distinguish local, CI, runtime, and
scheduled-task evidence.

## Publication

Commit logical units and push the integration branch. Integrate into `main`
only after required exact-head checks pass. Rename the GitHub repository only
after final `main` is healthy, then update `origin` and rerun required CI under
the new repository identity.
