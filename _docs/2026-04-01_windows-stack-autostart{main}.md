# 実装ログ: windows-stack-autostart

- 日付: 2026-04-01
- 目的: Windows起動時に TUI / GUI(API) / ブラウザ / ngrok を非同期で自動起動

## 変更内容

1. 追加
   - `scripts/windows/start-hermes-stack.ps1`
   - 機能:
     - Gateway 起動 (`py -3 -m hermes_cli.main gateway run`)
     - FastAPI 起動 (`py -3 -m hermes_api_server`)
     - ngrok 起動 (`ngrok http 8080`)
     - TUI 起動 (`py -3 -m hermes_cli.main`)
     - ブラウザ起動（既定 `http://127.0.0.1:8080/docs`）
   - 各プロセスは `Start-Process` で非同期起動
   - 既存プロセス検知（重複起動防止）を実装
   - ngrok起動失敗時は警告のみで継続

2. 更新
   - `scripts/windows/register-hermes-autostart.ps1`
   - 登録対象を `start-hermes-gateway.ps1` から `start-hermes-stack.ps1` に変更
   - タスク名/Startupランチャー名を Stack 用に変更

## 環境変数トグル

- `HERMES_AUTOSTART_GATEWAY` (default: true)
- `HERMES_AUTOSTART_API` (default: true)
- `HERMES_AUTOSTART_TUI` (default: true)
- `HERMES_AUTOSTART_BROWSER` (default: true)
- `HERMES_AUTOSTART_NGROK` (default: true)
- `HERMES_STARTUP_BROWSER_URL` (default: `http://127.0.0.1:8080/docs`)
- `HERMES_STARTUP_DELAY_SECONDS` (default: 20)

## 検証

- `register-hermes-autostart.ps1` 実行で Startup ランチャー作成を確認
- `start-hermes-stack.ps1` 実行で `Started: gateway/fastapi/ngrok/tui` を確認
- `gateway status` で稼働確認
- `http://127.0.0.1:8080/healthz` で `{status: ok}` 確認
- `tasklist` で `ngrok.exe` 稼働確認
