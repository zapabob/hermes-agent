# ハーネス拡張計画 — Plugin領域並行成長 (2026-09-03)

## 背景
- Step A+B完了: Generic Harness宣言 (`README.md`+`fork/harness/GENERIC_HARNESS.md`) と Antigravity隔離プラグイン (`plugins/hermes-antigravity`)
- 原則: narrow waist — coreは薄く、Edgesで伸ばす。Footprint Ladder準拠。upstream追従は `hermes-merge-conflict-strategies.json` の4分類で保護。

## 拡張の3本柱（Plugin隔離で並行）

### 1. 新プロバイダ / ローカル推論（plugins/model-providers/* or plugins/hermes-*）
既存43 provider + ローカル推論は充足。Ollamaは低速のため追加不要。
補完候補は必要最小限に留める:
- **Groq / Cerebras (fast inference)** — 超低遅延推論。既存openai互換だが専用providerでレート/モデル表を最適化。必要に応じPlugin隔離で追加。
- **Hypura (既存ローカルスケジューラ活用)** — `plugins/model-providers/hypura` 相当をローカルGGUFスケジューラとして昇格。NVMe階層・VRAM最適化をWindows特化で拡張。
> いずれも `providers.register_provider()` のPluginパターンで core無改修。`check_fn` で未設定時は非表示。Ollama等のローカル汎用推論は速度面で見送り。

### 2. 新ツール / スキル（skills/* or plugins/hermes-*）
記憶/RAGは `hakua-memory` + SemanticGraph + Ebbinghaus で実装済みのため追加不要。computer-use / browser-use も既存。
- **Windows自動化** — `windows-local-service-ops` 拡張: UAC/レジストリ/タスクスケジューラ/サービス操作を `check_fn: is_windows` gated tool化。既存 `tools/environments/*` は preserve_custom。
- **ファイル操作強化** — 大容量/差分/バイナリ対応の `hermes-file-ops` Plugin。coreの `read_file/write_file/patch` を補完。
> Skillは `SKILL.md` + `scripts/` で完結、Pluginは `register(ctx)` で tool登録。いずれも core tool追加なし。RAG/computer-use/browser-useは重複のため提案しない。

### 3. OSSサブモジュール（vendor/* + preserve_custom）
現状16 submodule。RAG/computer-use/browser-use は既存のため候補から除外。追加は「小さく・枯れて・Windowsで動く」を優先:

| 候補 | URL | 選定理由 | ライセンス | Windows | 運用注意 |
|------|-----|----------|------------|---------|----------|
| **comfyui** | `comfyanonymous/ComfyUI` | 画像生成のデファクト。既に `skills/comfyui` 的利用あるが vendor pinで再現性担保 | GPL-3.0 | ◎ (Desktop版あり) | サイズ大。`vendor/comfyui` は shallow pin + `preserve_custom`。CIは別jobで遅延実行 |
| **whisper.cpp** | `ggerganov/whisper.cpp` | ローカルSTT。VOICEVOX/音声パイプライン補完。GGUF的軽量 | MIT | ◎ | モデルは git LFS外。`vendor/whisper.cpp` + モデルは `H:\elt_data` 参照 |

> 追加手順: `git submodule add <url> vendor/<name>` → `scripts/merge_tools/hermes-merge-conflict-strategies.json` に `vendor/<name>/** → preserve_custom` 追記 → `git commit`。`--depth 1` 推奨。

## ガードレール（統合/リスク管理派より）
1. **Plugin隔離徹底** — Edge機能は必ず独立Plugin、coreへ混入禁止
2. **週次dry-runマージ検証** — `py -3 scripts/sync_all.py --dry-run` をCI/手動で実行、4分類と sanitizer通過を確認
3. **ドキュメント先行** — ADR/インターフェース仕様を先に確定（本MDが該当）
4. **段階的有効化** — `check_fn` gatingで段階ロールアウト、障害時即座無効化
5. **Footprint Ladder遵守** — 既存拡張→CLI+Skill→check_fn→standalone Plugin→MCP→新core tool の順でのみ昇格

単独メンテナでは core変更のblast radius最小化が生存戦略。Lv.4 (standalone Plugin) までで運用し、Lv.5/6は実績と自動検証が揃ってから。

## 次のアクション（本PRでは文書のみ、実装は後続PRで段階的）
- [ ] `vendor/whisper.cpp` 追加（小規模・MIT・Windows◎で最初の一手）
- [ ] `skills/windows-automation` 設計（UAC/レジストリ/タスクスケジューラ）
- [ ] 必要に応じ `plugins/model-providers/groq` 等の高速推論provider追加
- いずれも本MDマージ後に1件ずつPR化し、dry-run検証を経て mainへ。Ollama/RAG/browser-use/computer-useは実装済みのため追加しない

## 参照
- `fork/harness/GENERIC_HARNESS.md` — ハーネス定義正本
- `scripts/merge_tools/hermes-merge-conflict-strategies.json` — preserve_custom運用
- `plugins/hermes-antigravity/` — Plugin隔離の前例
