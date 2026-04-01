# 実装ログ: brain-context-wiring

- 日付: 2026-04-01
- 目的: ルート `AGENTS.md` から `brain/*.md` の参照導線を明示し、Hermes起動時に読み込ませる

## 変更内容

1. `AGENTS.md` に `brain/*.md` 参照リンク群を追加
2. `agent/prompt_builder.py` に `brain/*.md` ローダーを追加
   - 対象: `AGENT.md`, `AGENTS.md`, `Gemini.md`, `GOAL.md`, `HEARTBEAT.md`, `MEMORY.md`, `RIEMANN_TRANSCEIVER.md`, `VISION.md`, `YANG_MILLS_TRANSCEIVER.md`
   - 既存のコンテキスト注入フローへ連結
3. 起動時コンテキスト生成の検証
   - `build_context_files_prompt(...)` の出力に `brain/AGENT.md` / `brain/VISION.md` が含まれることを確認

## 補足

- `SOUL.md` は変更していない
- Markdown lint 警告は既存 `AGENTS.md` 起因のものが中心で、今回の導線実装とは独立
