# 実装ログ: hermes-hypura-path-probe

- 日時: 2026-04-01 11:40:31 +09:00
- 対象: Hermes が前提とする OpenAI 互換パスと Hypura `serve` の応答パスの切り分け
- 作業ディレクトリ: `C:\Users\downl\Desktop\hermes-agent-main\hermes-agent-main`

## 前提

- Hypura: `http://127.0.0.1:8080`（既に `hypura serve` が稼働中）
- Hermes は `model.base_url` を `http://host:port/v1` としたとき、OpenAI SDK 経由で `GET .../v1/models` と `POST .../v1/chat/completions` を利用する。

## フェーズ1: Hypura 単体（生存確認）

| リクエスト | HTTP | 結果 |
|------------|------|------|
| `GET http://127.0.0.1:8080/` | 200 | `{"status":"ok"}` |
| `GET http://127.0.0.1:8080/api/tags` | 200 | Ollama 形式の `models` 配列（GGUF 名を含む JSON） |

**結論**: Hypura 本体は正常応答。

## フェーズ2: Hermes 互換パス

| リクエスト | HTTP | 備考 |
|------------|------|------|
| `GET http://127.0.0.1:8080/v1/models` | **404** | Hermes の `_auto_detect_local_model` が期待する一覧 API なし |
| `POST http://127.0.0.1:8080/v1/chat/completions`（最小 OpenAI JSON） | **404** | Hermes のチャット推論経路なし |

**結論**: **`model.base_url` を Hypura のオリジンに合わせるだけでは Hermes は接続できない**（プロトコル不一致）。

## フェーズ3: 橋渡し方針（決定）

優先度の目安:

1. **B（中間プロキシ）— 推奨**  
   `POST /v1/chat/completions` と `GET /v1/models` を受け、Hypura の `POST /api/chat` 等へ変換する薄いプロキシを立て、Hermes は `http://127.0.0.1:<proxy>/v1` を向ける。Hermes 本体は変更不要。

2. **C（Ollama など別バックエンド）**  
   既に OpenAI 互換 `/v1` を出す Ollama 等へ寄せ、GGUF はそちらで配布・登録する。Hypura を Hermes の直バックエンドにはしない。

3. **D（Hypura 拡張）**  
   Hypura リポジトリ側に `/v1/chat/completions` と `/v1/models` を実装する。工数大・保守は Hypura 側。

**今回の推奨**: すぐ Hermes とつなぐなら **B**。長期的に一本化するなら **D** を検討。

## 再現コマンド（PowerShell）

```powershell
Invoke-WebRequest "http://127.0.0.1:8080/" -UseBasicParsing
Invoke-WebRequest "http://127.0.0.1:8080/api/tags" -UseBasicParsing
try { Invoke-WebRequest "http://127.0.0.1:8080/v1/models" -UseBasicParsing } catch { $_.Exception.Response.StatusCode.value__ }
$body = '{"model":"test","messages":[{"role":"user","content":"hi"}]}'
try {
  Invoke-WebRequest "http://127.0.0.1:8080/v1/chat/completions" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing
} catch { $_.Exception.Response.StatusCode.value__ }
```

**更新（案 B 実装後）**: Hermes の `model.base_url` は Hypura 直ではなく、プロキシの **`http://127.0.0.1:8090/v1`**（既定）を向ける。手順は [`2026-04-01_hypura-oai-proxy{main}.md`](2026-04-01_hypura-oai-proxy{main}.md)。
