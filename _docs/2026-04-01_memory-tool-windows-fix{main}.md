# 実装ログ: memory-tool-windows-fix

- 日付: 2026-04-01
- 事象: `Could not import tool module tools.memory_tool: No module named 'fcntl'`
- 影響: ツール初期化不全により TUI/チャネル応答が不安定化

## 対応

- `tools/memory_tool.py` を Windows 互換化
  - POSIX: `fcntl.flock`
  - Windows: `msvcrt.locking` へフォールバック
  - ロックファイルオープンを `a+` に変更

## 検証

- `py -3 -c "import tools.memory_tool as m; ..."` で import 成功を確認
