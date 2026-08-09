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
- hardening + Semantic Graph + Skill: **35 passed** via canonical `scripts/run_tests.sh`
- Hermes plugin regression: **68 passed** via canonical `scripts/run_tests.sh`
- canonical runner exit code: **0** for both scopes
- compileall / py_compile: exit 0
- git diff --check: exit 0
- The duration-cache persistence failure was subsequently made non-fatal in separate runner commit `be1ffaf5fe`; the remaining cache warning is diagnostic and non-blocking.

## 残留リスク
- repository 全体の full suite は未実行。
- duration-cache persistence remains degraded and best-effort under this Windows/MSYS worktree; it does not override authoritative test results.
- embedding なしの検索であり、語彙が完全に異なる paraphrase の recall は保証しない。
- `semantic_graph_feedback` の `user_confirmed` は model-facing API であり、人間の実確認を暗号学的には証明しない。
- purge の accepted node と evidence 保持ポリシーは別途 production gate で再確認する。

## 次の推奨アクション
1. この branch の diff をレビューし、main へ cherry-pick / merge する。
2. 既存の production profile では `capture_turns=true` / `auto_extract=all` を、運用 DB の backup と purge 方針確認後に段階的に有効化する。
3. runner の Windows Bad file descriptor を別 issue として再現・修正する。
4. human approval gate と purge の evidence retention を production readiness の P1 として設計する。

## 追加記録: runtime patch attempt

A subsequent attempted patch against `plugins/semantic_graph/runtime.py` did not apply because the target hunk no longer matched. No `runtime.py` modification was included in that turn. The verified Semantic Graph hardening remained at commit `41feb7f78b`.

## Live integration smoke

Environment:
- isolated `HERMES_HOME` under the workspace `_tmp` directory; no production profile or production database modified
- direct Python runtime invocation with `PYTHONPATH` set to this worktree
- Python 3.12.13, Windows/MSYS
- tested commit before the live-smoke follow-up: `da86af120f`
- the `hermes` executable on `PATH` resolves to the separate main worktree; it was not used as evidence for this p0 smoke

Results:
- plugin/runtime initialization: **PASS** — schema version 1, FTS enabled, empty isolated store
- explicit structured extraction: **not live-provider extraction**; provider credentials were intentionally absent. Explicit fragment submission and persistence boundary: **PASS**
- user and assistant artifacts: **PASS**
- user authority and evidence span: **PASS**
- Bearer/JSON-secret persistence check against stored SQLite records: **PASS**
- hidden reasoning persistence check: **PASS** — no hidden reasoning was supplied or stored
- restart recall: **PASS** — new runtime instance against the same isolated SQLite store recalled TypeScript in English and Japanese paraphrase; rendered context contained `data_only="true"`
- three-child provenance: **PASS** — 3 `subagent_start` and 3 `subagent_stop` events, sanitized summaries, status and duration fields present
- run-scoped export: **PASS** — run B content absent from run A export; artifacts stayed within the isolated export root
- correction history: **PASS** — old node superseded, replacement asserted, `supersedes` edge present, default recall returned the replacement
- live provider structured completion: **NOT RUN** — no provider key was placed in the isolated profile; this remains unverified

Follow-up hardening included metadata-key redaction and conservative Japanese-to-English recall expansion. Verification after those changes:

- targeted Semantic Graph tests: **36 passed**, canonical `scripts/run_tests.sh` exit 0
- Hermes plugin regression tests: **68 passed**, canonical `scripts/run_tests.sh` exit 0
- `py_compile` and `git diff --check`: **PASS**

## Final verification

Verified on Windows/MSYS using the canonical `scripts/run_tests.sh` runner after making duration-cache persistence non-fatal.

The Semantic Graph evidence was initially collected on commit `41feb7f78b` plus the then-uncommitted runner fix. The runner fix was subsequently committed separately as `be1ffaf5fe` (`fix(test-runner): make duration cache persistence best-effort`), and both scopes were re-run against that new HEAD.

### Semantic Graph scope

- 35 passed
- 0 failed
- runner exit code: 0
- HEAD: `be1ffaf5fe`

### Hermes plugin regressions

- 68 passed
- 0 failed
- runner exit code: 0
- HEAD: `be1ffaf5fe`

### Static checks

- `py -3 -m py_compile scripts/run_tests_parallel.py plugins/semantic_graph/*.py` — passed
- `git diff --check` — passed

### Environment

- Python: 3.12.13
- OS/shell: Windows 11 / Git Bash MSYS2 (`MINGW64_NT`, `MSYSTEM=MINGW64`)
- Runner workers: `HERMES_TEST_WORKERS=1`
- Verification date: 2026-08-09

The duration cache was saved successfully in the latest verification. Cache persistence remains best-effort and may emit a non-fatal warning if the destination becomes unavailable. This cache is optional scheduling metadata and cannot override the authoritative test result.

The full repository test suite and live-provider integration tests were not run. Real-profile enablement, structured extraction against a live provider, three-parallel-subagent provenance, and restart/reload SQLite recall were not run. Production readiness is therefore not claimed.

Remote reviewability remains unconfirmed; the branch was not pushed.

## Final status

```text
Semantic Graph MVP: implemented
P0 hardening: targeted verification passed
Canonical runner: exit 0 for both scopes
Plugin API regression: verified
Runner fix: committed separately at be1ffaf5fe
Full repository suite: not run
Live integration: not run
Production readiness: not reached
```
