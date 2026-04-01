# HEARTBEAT.md (Hermes Reflection Loop)

## Cadence

定期的に以下を点検し、必要なら小さな改善を積み上げる。

## Checklist

1. Health
   - CLI/Gatewayの起動状態
   - 主要依存の欠落有無
2. Safety
   - 秘密情報の露出リスク
   - 権限・承認フローの逸脱有無
3. Quality
   - 最近の失敗ログから再発パターンを抽出
   - テスト/静的解析で新規エラーがないか確認
4. Documentation
   - 運用上の重要変更を `_docs/` に追記

## Action Rule

- 問題発見時は「再現 -> 最小修正 -> 検証 -> 記録」の順で対処する。
