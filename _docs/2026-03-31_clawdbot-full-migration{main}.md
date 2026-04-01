# 実装ログ: clawdbot-full-migration

- 実行日時(UTC, MCP取得): `2026-03-31T14:51:19+00:00`
- 対象: `C:\Users\downl\Desktop\clawdbot-main3\clawdbot-main` -> `hermes-agent`
- ワークツリー名: `main`

## 実施内容

1. `hermes claw assess` コマンドを追加し、clawdbot系フォーク向けの全面移植診断を実装。
2. `docs/migration/clawdbot_migration_assessment.{json,md}` を生成し、機能棚卸しとENV差分を可視化。
3. `openclaw_to_hermes.py` を使って full preset の dry-run を実行し、移行可能範囲を実測。
4. `hermes_cli/env_loader.py` に OpenClaw 旧ENVキー互換aliasを実装（旧キーがある場合にHermesキーへ昇格）。
5. 移植実行ガイドとして以下を作成:
   - `docs/migration/clawdbot_full_porting.md`
   - `docs/migration/clawdbot_cutover_checklist.md`
6. `docs/migration/openclaw.md` に `hermes claw assess` フローを追記。
7. 追加実装に対して pytest を実行し、関連テストの通過を確認。

## 主な出力と結果

- `hermes claw assess` 結果:
  - extensions: 91
  - manual-port-required: 10
  - native-or-direct-mapping: 31
  - needs-review: 50
  - env overlap: 6 / 44 (source keys)
- `openclaw_to_hermes.py --preset full` dry-run:
  - migrated: 95
  - archived: 4
  - skipped: 25
  - conflict: 0
  - error: 0

## 備考

- 旧ENV互換aliasは Hermes側で新キー未設定時のみ適用されるため、安全に段階移行可能。
- `manual-port-required` に分類された独自拡張は段階的に skill/gateway/CLI へ再配置する前提。
