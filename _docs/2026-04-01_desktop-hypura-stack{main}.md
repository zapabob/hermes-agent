# 実装ログ: desktop-hypura-stack

- 日時: 2026-04-01（JST）
- 対象: デスクトップショートカット改良 + スタックで Hypura（GGUF）推論
- 作業ディレクトリ: `C:\Users\downl\Desktop\hermes-agent-main\hermes-agent-main`

## 変更内容

1. [`scripts/windows/start-hermes-stack.ps1`](../scripts/windows/start-hermes-stack.ps1)
   - `HERMES_AUTOSTART_HYPURA` / `HERMES_AUTOSTART_HYPURA_PROXY`（既定 true）で **Hypura `serve`** と **`hypura_oai_proxy`** を起動。
   - `HERMES_HYPURA_EXE` / `HERMES_HYPURA_GGUF`（既定はユーザーの hypura ビルド + EasyNovel 配下 GGUF）。
   - `HERMES_HYPURA_PORT`（既定 8080）、`HERMES_HYPURA_PROXY_PORT`（既定 8090）、`HERMES_HYPURA_LOAD_WAIT_SECONDS`（既定 15）。
   - Hypura 使用時は **8080 占有**のため、未設定または 8080 の **`HERMES_API_PORT` を 8765 に変更**し、`hermes_api_server` / ブラウザ / ngrok のトンネル先ポートと整合。
2. [`scripts/windows/create-hermes-desktop-shortcut.ps1`](../scripts/windows/create-hermes-desktop-shortcut.ps1)（新規）
   - `Hermes Hypura Stack.lnk` をデスクトップに生成（説明・作業ディレクトリ付き）。

## Hermes 側（手動 1 回）

`~/.hermes/config.yaml` で LLM をプロキシに向ける:

- `model.base_url: http://127.0.0.1:8090/v1`
- `model.provider: custom`
- `model.api_mode: chat_completions`
- `model.default`: `/v1/models` に出る ID（Hypura ロード中のモデル名）

## 結果

- デスクトップからワンクリックで **Hypura GGUF 推論 + OpenAI 互換プロキシ**を含むスタックが起動可能。
