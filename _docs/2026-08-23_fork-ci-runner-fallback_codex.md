# Fork CI runner fallback

Date: 2026-08-23

## Scope

The fork validation run for `b80d339837463c15c8eadb09726edff5f35909e9` left the JS/TS, Python, Windows, Rust, and Nix lanes queued for more than 26 minutes. The queued jobs requested the large hosted-runner labels used by the official repository, while the fork has no self-hosted runners.

## Change

The reusable JS/TS, Python, Rust, and Nix workflows now select the official large runner only when `github.repository` is `NousResearch/hermes-agent`; the fork selects `ubuntu-latest`. Fork timeouts are extended to preserve the same checks on the smaller runner. The official repository path remains unchanged.

## Evidence

- `origin/main` before this change: `b80d339837463c15c8eadb09726edff5f35909e9`.
- Main CI run `32576735826` and Nix run `32576735291` were canceled after remaining queued for more than 26 minutes.
- Docker Build, Test, and Publish, Fork CI/CD, auto-fix, local typecheck, focused tests, build, audit, and npm lock dry-run were green for `b80d339837463c15c8eadb09726edff5f35909e9`.
- The running Hermes Desktop, backend, gateway, llama, and watchdog services were not stopped for this change.

## Follow-up

Push this workflow-only change and require a fresh exact-SHA CI and Nix result before declaring cloud CI green.
