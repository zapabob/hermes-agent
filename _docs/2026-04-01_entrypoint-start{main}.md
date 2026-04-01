# 実装ログ: entrypoint-start

- 日時: 2026-04-01
- 対象: Hermes 起動エントリーポイント探索と起動確認
- 作業ディレクトリ: `C:\Users\downl\Desktop\hermes-agent-main\hermes-agent-main`

## 実施内容

1. `README.md` とコード検索から起動エントリーポイントを特定
   - CLI: `hermes` (`py -3 -m hermes_cli.main`)
   - Gateway: `hermes gateway` (`py -3 -m hermes_cli.main gateway ...`)
2. 既存ターミナル状態を確認し、Gateway が既に起動済みであることを確認
3. `py -3 -m pip install -r requirements.txt` を実行し、欠落依存 (`fire`) を解消
4. 文字コード問題対策として `PYTHONIOENCODING=utf-8` を指定して実行
5. `py -3 -m hermes_cli.main gateway status` で稼働確認
6. `py -3 -m hermes_cli.main gateway start` は Windows で `Not supported on this platform.` を確認
7. 代替として `scripts/windows/start-hermes-gateway.ps1` を実行し、起動経路を確立
8. 再度 `gateway status` で起動 PID を確認

## 結果

- Gateway は起動状態を確認済み
- CLI 起動の依存不足は解消済み
- Windows では `gateway start` 直実行より、`start-hermes-gateway.ps1` 利用が有効

## 補足

- `--help` 実行時は cp932 で UnicodeEncodeError が出るため、PowerShell では UTF-8 指定を推奨
