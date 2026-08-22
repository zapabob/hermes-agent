# Main Clean and CI Closeout

- Date: 2026-08-22
- Agent: Codex
- Baseline: `5c3c06a306f71c7b224d8aa297e177fe799c33a7`
- Scope: publish the intended canonical `main` changes while preserving the running Hermes stack and local review evidence.

## Changes

- Preserved the existing Desktop backend resiliency changes in `apps/desktop/electron/main.ts`.
- Fixed the remaining `preview.act.respond` path in `apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/desktop-bridge.ts` so replies use the originating gateway scope consistently.
- Regenerated `package-lock.json` from the tracked workspace manifests. The previous push-SHA auto-fix and JavaScript CI runs failed because npm 12 could not reconcile the stale lock metadata with the installed workspace dependency graph.

## Local verification

- `pnpm --filter hermes typecheck`: passed for renderer, Electron, and E2E TypeScript projects.
- Targeted ESLint for the changed Desktop files: 0 errors; five existing padding warnings remain in `main.ts`.
- Gateway source-routing tests: 4 passed.
- Gateway scope tests: 4 passed.
- Backend ownership and parent-process identity tests: 25 passed.
- `pnpm --filter hermes build`: passed; renderer, Electron bundle, native dependency staging, and dist assertion completed.
- `npm ci --ignore-scripts --dry-run`: passed after lock regeneration.
- `npm audit --audit-level=high --workspaces=false`: 0 vulnerabilities.

## Evidence and runtime boundary

- Local `.omo/evidence` files were moved, not deleted, to `C:\Users\downl\AppData\Local\Temp\hermes-worktree-evidence-20260822`.
- The running Desktop, managed backend, watchdog, WebUI, Dashboard, Llama, Gateway, and Harness were left untouched during this closeout.
- Cloud CI/CD status for the final pushed SHA remains a separate publication gate and must be recorded after the push completes.
