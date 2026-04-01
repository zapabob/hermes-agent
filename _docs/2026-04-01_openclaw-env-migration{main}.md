# 実装ログ: openclaw-env-migration

- 日付: 2026-04-01
- 目的: OpenClaw の環境変数を Hermes に移植（上書き方針）
- コピー元:
  - `C:\Users\downl\Desktop\clawdbot-main3\clawdbot-main\.env`
  - `C:\Users\downl\Desktop\clawdbot-main3\clawdbot-main\openclaw.json`（未検出）
- コピー先:
  - `C:\Users\downl\.hermes\.env`
  - `C:\Users\downl\.hermes\config.yaml`

## 実施内容

1. バックアップ作成
   - `C:\Users\downl\.hermes\.env.bak-20260401-030018`
   - `C:\Users\downl\.hermes\config.yaml.bak-20260401-030018`
2. マッピング仕様
   - `TELEGRAM_CHAT_ID` は `.env` にそのまま反映（既存値一致のため変更なし）
   - `OPENCLAW_GATEWAY_TOKEN` を `.env` に反映
   - 互換性のため `HERMES_GATEWAY_TOKEN` にも同じ値を反映
3. 実更新（`~/.hermes/.env`）
   - `HERMES_GATEWAY_TOKEN` を上書き
   - `OPENCLAW_GATEWAY_TOKEN` を上書き
4. `~/.hermes/config.yaml`
   - 対象キーに対応する追加変更なし（既存構成を維持）

## 検証

- `hermes config show` 実行: 正常表示（モデル設定維持）
- `py -3 -m hermes_cli.main gateway status` 実行: Gateway running
- `.env` 主要キー確認:
  - `HERMES_GATEWAY_TOKEN` 設定あり
  - `OPENCLAW_GATEWAY_TOKEN` 設定あり
  - `TELEGRAM_CHAT_ID` 設定あり

## 注意

- 秘密値はログ上マスク運用し、本ファイルには平文トークンを記載しない。
