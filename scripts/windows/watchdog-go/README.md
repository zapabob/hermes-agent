# Hermes Go Watchdog（Windows）

Hermes Desktop（`Hermes.exe`）と Desktop が spawn する `hermes serve` バックエンドを**相互監視**する独立プロセスです。  
**Hermes Agent の plugin / tool / skill / MCP / cron には一切登録しません。**

## 隔離（AI から制御不可）

| 項目 | 内容 |
|------|------|
| プロセス | Hermes Python/Electron とは別バイナリ |
| 設定 | `%LOCALAPPDATA%\HermesWatchdog\`（ロック・状態 JSON） |
| ログ | `%HERMES_HOME%\logs\hermes-go-watchdog.log` |
| 変更 API | `HERMES_WATCHDOG_ADMIN_TOKEN` 必須（未設定なら **403**） |
| 読取 API | `GET /health`, `GET /api/status`（ローカル / tailnet） |

## ビルド

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\Build-HermesGoWatchdog.ps1
```

成果物: `scripts\windows\watchdog-go\dist\hermes-watchdog.exe`

## 起動

```powershell
# 環境変数（例）
$env:HERMES_WATCHDOG_ADMIN_TOKEN = "<operator-secret>"
$env:HERMES_WATCHDOG_TS_AUTHKEY = "<ts-authkey>"   # 任意: tsnet 有効化

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\Start-HermesGoWatchdog.ps1
```

### フラグ（Start スクリプト経由）

| フラグ | 既定 | 説明 |
|--------|------|------|
| `-IntervalSec` | 20 | 監視周期 |
| `-FailThreshold` | 2 | `-ManageDesktop` 時の backend 連続失敗しきい値 |
| `-Once` | off | 1 周期だけ実行して終了 |
| `-ManageDesktop` | off | 明示時のみ Desktop の起動・再起動を許可 |
| `-HotSwap` | off | 候補 exe を検証ビルドし、watchdog だけを差し替えて `/health` を確認 |
| `-NoTsnet` | off | tsnet を強制 OFF |
| `-Listen` | 127.0.0.1:9920 | ローカル HTTP |

## Tailscale（tsnet）

1. Tailscale 管理画面で **auth key** を発行（推奨: reusable + タグ付き）
2. 環境変数 `HERMES_WATCHDOG_TS_AUTHKEY` または `TS_AUTHKEY` に設定（**リポジトリにコミットしない**）
3. 起動すると tailnet 上で `hermes-watchdog` として `:443` で待受
4. 他ノードから: `curl -k https://hermes-watchdog/health`（MagicDNS / ホスト名）

## HTTP API

| Method | Path | 認証 | 説明 |
|--------|------|------|------|
| GET | `/health` | 不要 | 生存確認 |
| GET | `/api/status` | 不要 | ウォッチドッグ状態 JSON |
| POST | `/api/v1/pause` | Admin | 監視一時停止 |
| POST | `/api/v1/resume` | Admin | 監視再開 |
| POST | `/api/v1/cycle` | Admin | 即時 1 周期 |
| POST | `/api/v1/stop` | Admin | Graceful stop |

Admin 認証: `Authorization: Bearer <token>` または `X-Admin-Token: <token>`

## 監視ロジック

1. **起動時 prewarm（非同期）** — HTTP / RunLoop 起動後に goroutine で managed `hermes serve --skip-build`（既定 `:9118`）を立ち上げ、`%LOCALAPPDATA%\HermesWatchdog\desktop-backend.json` に URL/token/port を原子的に公開する。cold start で制御プレーンをブロックしない
2. 標準では `Hermes.exe` の不在を記録するだけで、Desktop を起動・再起動しない。headless 運用や手動起動の Desktop に干渉しないためである
3. Desktop 生存 + backend 不在 → managed serve を起動・復旧する。回復しない場合も、標準では Desktop を停止しない
4. `-ManageDesktop` を明示した場合のみ、Desktop 不在時の起動と、連続失敗が `-FailThreshold` 以上の再起動を許可する。WMI 取得失敗は停止と見なさず、Desktop には触れない
5. 予約 ops ポート (9119/9120/8787/…) は backend 判定・reap 対象外。watchdog-managed serve は固定 `:9118` を使う

### Desktop ショートカット

パッケージ `Hermes.exe` 直起動は `HERMES_DESKTOP_*` を付けない。Go watchdog が prewarm していれば Desktop は `desktop-backend.json` を読んで **15s 以内** に既存 serve へ接続する（`apps/desktop/electron/watchdog-backend.ts`）。

## 追加フラグ（exe / Start スクリプト）

| フラグ | 既定 | 説明 |
|--------|------|------|
| `-prewarm-backend` | on | serve の prewarm / 常時監督 |
| `-managed-backend-port` | 9118 | watchdog 管理の固定 serve ポート（9120/8787/9119 とは別） |
| `-manage-desktop` | off | packaged Desktop の起動・再起動を明示的に許可 |
| `-backend-start-timeout` | 300 | `/api/status` 待ち (秒) |
| `-backend-ready-timeout` | 180 | 追加の `/api/status` 待ち (秒) |

## 監視ロジック（旧 PowerShell 版との差分）

## 停止

- タスクマネージャで `hermes-watchdog.exe` を終了
- または Admin API: `POST /api/v1/stop` + Bearer token
- ロック: `%LOCALAPPDATA%\HermesWatchdog\watchdog.lock`

## ホットスワップ

次の実行は、候補 exe を `hermes-watchdog.next.exe` としてビルドし、既存 watchdog を graceful stop（管理トークン未設定時のみ強制停止）した後に原子的に置換する。`Hermes.exe`、既存の `hermes serve`、dashboard は停止しない。新しい watchdog の `/health` が制限時間内に応答しなければ、直前の exe に戻して起動を試みる。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\Start-HermesGoWatchdog.ps1 -HotSwap -RunBuildTests
```

別の作業ツリーで候補をビルドし、稼働用 exe だけを差し替える場合は `-RuntimeExe <live hermes-watchdog.exe path>` を `-HotSwap` と併用する。

## スタック再起動との関係

`restart-hermes-stack.ps1 -StartGoWatchdog` で**明示指定時のみ**起動（既定 OFF）。  
既存 `dist/hermes-watchdog.exe` があれば rebuild しない。欠落時のみ `BuildIfMissing`（SkipTest・180s タイムアウト）。失敗時はスタック全体を止めず watchdog 起動をスキップ。  
Hermes Agent からは到達不可。
