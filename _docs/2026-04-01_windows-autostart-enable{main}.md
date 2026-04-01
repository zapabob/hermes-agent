# 実装ログ: windows-autostart-enable

- 日付: 2026-04-01
- 目的: Windows 電源投入後のログオン時に Hermes Gateway を自動起動

## 実施内容

1. 既存の自動起動ランチャーを確認
   - `C:\Users\downl\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\HermesAgentGatewayAutoStart.cmd`
2. 登録スクリプトを再実行
   - `scripts/windows/register-hermes-autostart.ps1`
3. Task Scheduler 登録は権限不足で失敗し、フォールバックで Startup ランチャーを再生成

## 結果

- Startup フォルダ経由の自動起動導線が有効
- 次回の電源投入後、ユーザーログオン時に Hermes Gateway が自動起動する構成

## 補足

- 現在の稼働確認:
  - `py -3 -m hermes_cli.main gateway status` -> running
