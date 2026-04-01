# 実装ログ: hypura-oai-proxy

- 日時: 2026-04-01 11:45:02 +09:00
- 対象: Hypura `serve` 向け OpenAI 互換プロキシ（案 B）
- 作業ディレクトリ: `C:\Users\downl\Desktop\hermes-agent-main\hermes-agent-main`

## 追加ファイル

- [`hypura_oai_proxy.py`](../hypura_oai_proxy.py) — `GET /v1/models`（→ `/api/tags`）、`POST /v1/chat/completions`（→ `/api/chat`、NDJSON→OpenAI SSE）、`GET /healthz`

## 環境変数

| 変数 | 既定 | 説明 |
|------|------|------|
| `HYPURA_OAI_UPSTREAM` | `http://127.0.0.1:8080` | Hypura `serve` のベース URL |
| `HYPURA_DEFAULT_MODEL` | 空 | リクエストに `model` が無いときの ID（未設定時は `/api/tags` 先頭） |
| `HYPURA_OAI_PROXY_HOST` | `127.0.0.1` | プロキシの bind |
| `HYPURA_OAI_PROXY_PORT` | `8090` | プロキシのポート（Hypura と重複させない） |
| `HYPURA_OAI_READ_TIMEOUT` | `1800` | 上流 httpx `read` 秒 |
| `HYPURA_OAI_LOG_LEVEL` | `INFO` | `logging` レベル |

## 起動例

1. Hypura を先に起動（例: ポート 8080）。
2. プロキシ:

```powershell
cd C:\Users\downl\Desktop\hermes-agent-main\hermes-agent-main
py -3 -m uvicorn hypura_oai_proxy:app --host 127.0.0.1 --port 8090
```

または:

```powershell
py -3 -m hypura_oai_proxy
```

（`main()` が `HYPURA_OAI_PROXY_*` を参照）

## Hermes 設定例（`~/.hermes/config.yaml`）

```yaml
model:
  provider: custom
  base_url: http://127.0.0.1:8090/v1
  api_mode: chat_completions
  default: Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-BF16
```

API キーが要る場合は `~/.hermes/.env` に `OPENAI_API_KEY=dummy` など（プロキシは未使用でも可）。

## 検証（実施済み）

- `GET http://127.0.0.1:8090/healthz` → 200
- `GET http://127.0.0.1:8090/v1/models` → 200、OpenAI 形式の `data[]`
- `POST /v1/chat/completions` + `stream: true` → `text/event-stream`、SSE `data:` 行
- `openai` Python SDK で `base_url=http://127.0.0.1:8090/v1` + `stream=True` で 1 往復

## 制限

- ツール呼び出しは Hypura 側が実質未対応のため、Hermes でツール有効セッションでは失敗し得る（チャットのみ想定）。
- 上流は `POST /api/chat` の NDJSON を前提とする。

## スタック起動（Windows）

[`scripts/windows/start-hermes-stack.ps1`](../scripts/windows/start-hermes-stack.ps1) が **Hypura `serve`（GGUF）** と **`hypura_oai_proxy`** を既定で先に起動する（`HERMES_AUTOSTART_HYPURA` / `HERMES_AUTOSTART_HYPURA_PROXY`）。  
GGUF パスは **`HERMES_HYPURA_GGUF`**、Hypura 実行ファイルは **`HERMES_HYPURA_EXE`** で上書き可。

デスクトップショートカット:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\create-hermes-desktop-shortcut.ps1
```

生成例: `Desktop\Hermes Hypura Stack.lnk` → `start-hermes-stack.ps1`。

Hypura 使用時は **8080** を占有するため、同スクリプトは **`HERMES_API_PORT=8765`**（未設定または 8080 のとき）で Hermes FastAPI（`hermes_api_server`）を起動し、ブラウザ既定 URL も `8765/docs` に合わせる。

## 関連

- 切り分け前提: [`2026-04-01_hermes-hypura-path-probe{main}.md`](2026-04-01_hermes-hypura-path-probe{main}.md)
