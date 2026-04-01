# 実装ログ: fastapi-wrapper

- 日付: 2026-04-01
- 目的: Hermes に最小 FastAPI ラッパー (`/healthz` `/status` `/send`) を追加

## 変更内容

1. 追加ファイル
   - `hermes_api_server.py`
2. 追加エンドポイント
   - `GET /healthz` : 生存確認
   - `GET /status` : Gateway 稼働状態（取得失敗時は `gateway_error` を返却）
   - `POST /send` : Hermes へメッセージ送信して応答を取得

## 実装方針

- 既存 `AIAgent` を直接利用し、薄いHTTP層のみ追加
- 共有ロックで同時実行競合を回避
- Windows環境で `gateway.status` 例外が出るケースを吸収し、API全体は正常応答を維持

## 検証

- `py -3 -m py_compile hermes_api_server.py`
- `fastapi.testclient` で `/healthz` `/status` 応答を確認
