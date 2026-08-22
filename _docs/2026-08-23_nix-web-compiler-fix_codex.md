# Nix web compiler typecheck fix

Date: 2026-08-23

## Failure

Nix run `32581971905` for commit `c239403985f626feb75ad1f08b4c8266faa12653` reached the standard fork runner but failed while building `web`. TypeScript reported TS18048 because the React Compiler preset type marks `rolldown.filter` as optional, while `web/vite.config.ts` assigned `.code` directly.

## Change

Initialize `preset.rolldown.filter` before assigning the scoped code filter in `web/vite.config.ts`, `web/vitest.config.ts`, and `apps/desktop/vite.config.ts`. This preserves the existing filter expression and covers the shared configuration pattern used by the web, Vitest, and Desktop paths.

## Verification

- `pnpm --filter web typecheck` passed.
- `pnpm --filter web build` passed with only the existing Vite `__dirname` native-config warning.
- The failed Nix run is retained as evidence; a fresh exact-SHA Nix run is required after push.
