# 実装ログ: provider-routing-fix

- 日付: 2026-04-01
- 事象: `ollama/qwen-Hakua-core2` 指定でも `openai-codex` で実行される

## 原因

- `requested=auto` の場合、`auth.json` の `active_provider` が優先されるため、
  OpenAI Codex ログイン状態があると `openai-codex` が選ばれる。

## 対応

- `model.provider=custom` を設定して auto 解決を回避
- `model.default=qwen-Hakua-core2` を設定
- `model.base_url=http://127.0.0.1:11434/v1` に修正（OpenAI互換 `/v1`）
- `model.api_mode=chat_completions` を設定

## 確認

- `resolve_runtime_provider()` の戻りが
  - `provider=custom`
  - `api_mode=chat_completions`
  - `base_url=http://127.0.0.1:11434/v1`
  となることを確認。
