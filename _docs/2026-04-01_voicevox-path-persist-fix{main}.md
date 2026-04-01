# 実装ログ: voicevox-path-persist-fix

- 日付: 2026-04-01
- 目的: `VOICEVOX_CLI_PATH` のユーザー環境変数永続設定を反映し、起動スタックで VOICEVOX を確実起動

## 実施内容

1. ユーザー環境変数設定
   - `setx VOICEVOX_CLI_PATH "C:\\Users\\downl\\AppData\\Local\\Programs\\VOICEVOX\\vv-engine\\run.exe"`
2. 新規セッションで反映確認
   - `[Environment]::GetEnvironmentVariable("VOICEVOX_CLI_PATH", "User")`
3. スクリプト修正
   - `start-hermes-stack.ps1` が `Process` 環境変数のみ参照していたため、
     `User` 環境変数をフォールバック参照する `Get-EnvValue` を追加
4. 再起動実験
   - `start-hermes-stack.ps1` 実行で `Started: voicevox` を確認

## 結果

- ToDo 3件を完了
- ユーザー環境変数ベースで VOICEVOX 自動起動が動作
