# Desktop ESLint import-order fix

Date: 2026-08-23

## Failure

Main CI run `32582630783` for commit `c8b3f555fb7e97b04042db47fec95b5c57c1a9d4` failed only in `apps/desktop :: check:lint`. The perfectionist import-order rule required the type-only `IconType` import to precede the value imports in `apps/desktop/src/lib/brand-icon.ts` and `apps/desktop/src/lib/mcp-brands.tsx`.

## Change

Move `type IconType` to the beginning of each `@icons-pack/react-simple-icons` import block. No runtime behavior or dependency is changed.

## Verification

- Targeted ESLint passed for both changed files.
- A fresh exact-SHA main CI run is required after push.
- The existing auto-fix PR #77 remains separate; this correction is included directly on `main` so the requested main branch gate can complete.
