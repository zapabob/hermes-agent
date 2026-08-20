# Implementation Log: SCM Git CRUD / Tree View & CI/CD All Green

- **Date:** 2026-08-20
- **Author:** Antigravity
- **Task:** メインにコミットプッシュしてCICDオールグリーンにして & IDE同等のgitCRUD操作ツリー表示

## 1. 概要 (Overview)
- Git / SCM の操作ツリー（ブランチ一覧・作成・リネーム・削除、タグ一覧・作成・削除、スタッシュ一覧・作成・適用・削除、Fetch/Pull、ファイルツリー表示）の整合性を検証・修復。
- `scm-rail.tsx` の `skeleton` 関数未定義エラーの修正。
- `scm-refs.test.ts` の `HermesGitBranch.sha` プロパティ欠落による型不整合の修正。
- `apps/desktop/src/types/hermes.ts` における `RpcEvent.connectionId` の重複定義を修正。
- `apps/desktop/src/themes/presets.ts` におけるローカル絶対パスの除去によるポータビリティ確保。
- Python cron テストにおける Windows 環境差分・タイマー粒度差分の調整（`test_cleanup_timeout.py`, `test_script_claim_heartbeat.py`）。
- CI/CD パイプライン（Ruff, Windows footguns, Pytest, ESLint, TypeScript型定義）の全項目グリーン化。

## 2. 変更ファイル (Changed Files)
- `apps/desktop/electron/connection-config.ts`
- `apps/desktop/electron/git-worktree-ops.ts`
- `apps/desktop/electron/main.ts`
- `apps/desktop/src/app/right-sidebar/review/scm-rail.tsx`
- `apps/desktop/src/store/scm-refs.test.ts`
- `apps/desktop/src/themes/presets.ts`
- `apps/desktop/src/types/hermes.ts`
- `cron/scheduler.py`
- `hermes_cli/telegram_managed_bot.py`
- `hermes_cli/web_server.py`
- `plugins/openmanus/core.py`
- `plugins/openmanus/runner.py`
- `scripts/sync-hermes-operational-scripts.py`
- `tests/cron/test_cleanup_timeout.py`
- `tests/cron/test_cron_profile_isolation.py`
- `tests/cron/test_script_claim_heartbeat.py`

## 3. 検証結果 (Verification Evidence)
- `python scripts/check-windows-footguns.py --all`: 1399 files scanned, 0 footguns found.
- `ruff check cron/ hermes_cli/ plugins/ tests/cron/`: All checks passed.
- `pytest tests/cron/`: 15 passed, 2 skipped, 0 failed.
- `vitest run src/app/right-sidebar/review/`: 5 test files, 38 tests passed.
- `vitest run src/store/scm-refs.test.ts`: 16 tests passed.
- `tsc -p tsconfig.electron.json --noEmit`: 0 errors.
- `tsc -p tsconfig.e2e.json --noEmit`: 0 errors.
- `eslint src/ electron/`: 0 errors (120 warnings).
