# 実装ログ: voicevox-tui-autostart

- 日付: 2026-04-01
- 目的: 起動スタックに VOICEVOX CLI 起動を追加し、TUI 起動実験を実施

## 変更内容

- `scripts/windows/start-hermes-stack.ps1` に VOICEVOX 自動起動処理を追加
  - トグル: `HERMES_AUTOSTART_VOICEVOX` (default: true)
  - 実行パス: `VOICEVOX_CLI_PATH` (default: `voicevox`)
  - 起動引数: `VOICEVOX_CLI_ARGS` (default: `--host 127.0.0.1 --port 50021`)
  - 失敗時はスタック全体を止めず Warning のみ

## 起動実験結果

- `start-hermes-stack.ps1` 実行で `Started: tui` を確認
- プロセス確認で TUI (`hermes_cli.main` 非 gateway) が `running`
- VOICEVOX はこの環境で実行ファイル未検出（Warning）
  - `~/.hermes/logs/voicevox-autostart-error.log` 生成を確認

## 補足

- VOICEVOX を確実起動するには `VOICEVOX_CLI_PATH` に実行ファイルの絶対パスを設定する。
