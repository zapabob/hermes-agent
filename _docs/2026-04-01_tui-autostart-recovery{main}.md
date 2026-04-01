# 実装ログ: tui-autostart-recovery

- 日時: 2026-04-01 05:07:28 +09:00
- 対象: TUI が開かない問題の復旧
- 作業ディレクトリ: `C:\Users\downl\Desktop\hermes-agent-main\hermes-agent-main`

## 原因

- `scripts/windows/start-hermes-stack.ps1` の `Is-TuiRunning` 判定が広すぎて、`hermes_cli.main chat -q ...` の単発CLIプロセスまで「TUI稼働中」と誤認。
- その結果、TUI起動ブロックがスキップされ、実際にはTUIウィンドウが開かない状態になっていた。

## 実施変更

1. `Is-TuiRunning` の除外条件を追加。
   - `-q` / `--query` を含む単発実行を除外し、対話TUIのみを稼働判定対象にした。
2. TUI起動コマンドを `cmd /c` から `powershell.exe -NoExit` に変更。
   - 起動後もコンソールを保持し、TUIの対話に入りやすくした。
3. `start-hermes-stack.ps1` を TUI 単体モードで再実行し、`Started: tui (PID: ...)` を確認。

## 結果

- スタック起動時にTUI起動処理が再び実行される状態へ復旧。
- 誤検知で起動スキップされる不具合を解消。

## 補足

- 既存の `-q` 単発テストプロセスが残っていると、将来的にも似た誤検知が起こり得るため、今回の除外条件追加で恒久的に回避できる。
