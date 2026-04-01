# 実装ログ: desktop-shortcut

- 日付: 2026-04-01
- 目的: デスクトップショートカットで Hermes スタック起動を可能にする

## 実施内容（更新）

1. **推奨**: [`scripts/windows/create-hermes-desktop-shortcut.ps1`](../scripts/windows/create-hermes-desktop-shortcut.ps1) を実行してショートカットを生成・更新する。
   - 既定名: `Hermes Hypura Stack.lnk`（デスクトップ）
   - 説明文に Hypura GGUF / OAI プロキシを明記
   - アイコン: PowerShell 既定（任意で `-IconPath` を指定可能）
2. 手動の場合（従来）
   - Target: `powershell.exe`
   - Arguments: `-NoProfile -ExecutionPolicy Bypass -File "<repo>\scripts\windows\start-hermes-stack.ps1"`
   - WorkingDirectory: リポジトリルート

## 結果

- ショートカットから `start-hermes-stack.ps1` が起動し、**Hypura（GGUF）+ `hypura_oai_proxy` + Gateway + TUI 等**が順に立ち上がる（環境変数で個別 OFF 可）。
