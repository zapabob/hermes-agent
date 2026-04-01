# 実装ログ: gateway-winerror87-fix

- 日付: 2026-04-01
- 事象: TUI / LINE / Telegram への返答がなく、Gateway が実質起動できていなかった

## 原因

- `gateway/status.py` の PID 生存確認で `os.kill(pid, 0)` が Windows 環境で
  `OSError: [WinError 87]` を投げ、起動フローが途中で停止していた。

## 対応

1. `gateway/status.py`
   - `get_running_pid()` の PID 生存確認例外に `OSError` を追加。
2. 起動スクリプトの安定化
   - `start-hermes-gateway.ps1` / `start-hermes-stack.ps1` の Gateway 起動コマンドを
     UTF-8 環境変数付きで実行。

## 検証

- `py -3 -m hermes_cli.main gateway run --replace` が例外で即落ちしないことを確認。
- `py -3 -m hermes_cli.main gateway status` で running 表示を確認。
