# 実装ログ: brain-guidelines-rewrite

- 日付: 2026-04-01
- 目的: clawdbot 側 brain 指針を Hermes 用にリライトして移植
- 制約: `SOUL.md` は書き換え禁止のため未編集

## 対応内容

以下を Hermes 側 `brain/` に新規作成:

- `AGENT.md`
- `AGENTS.md`
- `Gemini.md`
- `GOAL.md`
- `HEARTBEAT.md`
- `MEMORY.md`
- `RIEMANN_TRANSCEIVER.md`
- `VISION.md`
- `YANG_MILLS_TRANSCEIVER.md`

## 方針

- 元文書の危険/違法/不正アクセスを想起させる記述は除去
- Hermes の開発・運用実務に即した安全ガイドラインへ再構成
- 監査性、再現性、最小差分、ドキュメント運用を明示

## 非対応

- `SOUL.md` の改変（ユーザー指示により禁止）
