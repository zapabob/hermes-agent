# Semantic Graph P0/P1 Hardening 実装ログ

## 概要
Semantic Graph Memory MVP のレビュー指摘に対し、P0/P1 hardening を別 worktree で実装した。

## 背景・要求
対象は `plugins/semantic_graph`。main worktree の無関係な未追跡ファイルを変更せず、`fix/semantic-graph-p0-issues` ブランチで以下を修正した。

- 全永続化境界での secret / PII redaction
- fragment 適用の atomic transaction
- authority/status の降格防止
- run 単位の finalize / search / export 分離
- Hermes の `child_*` subagent hook 契約
- English / Japanese の限定的な自然言語 recall
- search schema の filter 実効化
- evaluation reference node の受け渡し

## 前提・判断
- core の `agent.redact.redact_sensitive_text` を第一段として呼び、semantic graph 固有の redaction を後段に適用する。
- DB 操作は既存の connection-per-operation API を維持しつつ、thread-local active connection により transaction 内の nested store methods を同一 connection へ束ねる。
- embedding や外部 DB は追加しない。検索改善は FTS OR terms と LIKE / CJK bigram fallback の範囲に限定する。
- human confirmation 境界の完全な再設計は別課題として残す。既存の feedback API 契約は今回変更していない。

## 変更対象ファイル
- `plugins/semantic_graph/sanitize.py`
- `plugins/semantic_graph/store.py`
- `plugins/semantic_graph/graph.py`
- `plugins/semantic_graph/exporter.py`
- `plugins/semantic_graph/runtime.py`
- `plugins/semantic_graph/retrieval.py`
- `tests/plugins/test_semantic_graph_hardening.py`

## 実装詳細
### Redaction
- Bearer header を generic assignment より先に完全置換。
- JSON key、quoted assignment、通常の assignment を redaction。
- core redactor を persistence sanitizer の第一段に追加。
- `sanitize_value()` を追加し、run / artifact / node / edge / evidence / fragment / evaluation / event の各 store write entry point で再帰的に適用。
- metadata、payload、notes、rationale、title、objective 等へ文字数・byte budget を適用。

### Atomicity / authority
- `SemanticGraphStore.transaction()` を追加。
- fragment apply は fragment row、node、edge、evidence、evaluation、run link を一 transaction で処理。
- mid-apply exception 時の rollback と retry を回帰テスト化。
- user / system 等の高 authority と accepted / asserted / rejected / superseded の状態を低 authority ingest で降格させない。

### Scope / lifecycle / retrieval
- `list_nodes_for_run()`、`list_edges_for_run()`、`list_evaluations_for_run()` を追加。
- finalize promotion は run-scoped node と stable evaluation target ID を利用。
- run 指定 export は対象 run の node / edge のみ出力。
- subagent hook は `child_subagent_id`、`child_goal`、`child_summary`、`child_status`、`duration_ms` 等を優先し旧 alias も維持。
- search は `subtypes`、`authorities`、`run_id` を FTS / LIKE 両方で適用。
- phrase-only search を廃止し、英語 OR terms と CJK bigram fallback を使用。
- `reference_node_ids` を evaluator に渡す。

## 実行コマンド
```text
py -3 -m pytest tests/plugins/test_semantic_graph_hardening.py tests/plugins/test_semantic_graph_registration.py tests/plugins/test_semantic_graph_store.py tests/plugins/test_semantic_graph_graph.py tests/plugins/test_semantic_graph_hooks.py tests/plugins/test_semantic_graph_inference.py tests/plugins/test_semantic_graph_exporter.py tests/plugins/test_semantic_graph_cli.py tests/skills/test_semantic_graph_memory_skill.py -q -o addopts= -p no:randomly -p no:cacheprovider

py -3 -m pytest tests/hermes_cli/test_plugins.py tests/agent/test_plugin_llm.py -q -o addopts= -p no:randomly -p no:cacheprovider

py -3 -m compileall -q plugins/semantic_graph
git diff --check
```

## テスト・検証結果
- hardening + Semantic Graph + Skill: **35 passed**
- Hermes plugin regression: **68 passed**
- compileall: exit 0
- git diff --check: exit 0
- `scripts/run_tests.sh` はこの Windows/MSYS 環境で既知の `Bad file descriptor` 終了障害があるため、テスト証拠には直接 pytest の結果を使用した。

## 残留リスク
- repository 全体の full suite は未実行。
- Windows/MSYS 標準 runner の descriptor lifecycle 問題は未修正。
- embedding なしの検索であり、語彙が完全に異なる paraphrase の recall は保証しない。
- `semantic_graph_feedback` の `user_confirmed` は model-facing API であり、人間の実確認を暗号学的には証明しない。
- purge の accepted node と evidence 保持ポリシーは別途 production gate で再確認する。

## 次の推奨アクション
1. この branch の diff をレビューし、main へ cherry-pick / merge する。
2. 既存の production profile では `capture_turns=true` / `auto_extract=all` を、運用 DB の backup と purge 方針確認後に段階的に有効化する。
3. runner の Windows Bad file descriptor を別 issue として再現・修正する。
4. human approval gate と purge の evidence retention を production readiness の P1 として設計する。
