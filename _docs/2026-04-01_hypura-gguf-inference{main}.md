# 実装ログ: hypura-gguf-inference

- 日時: 2026-04-01 11:32:55 +09:00
- 対象: Hypura (`hypura.exe run`) で同一 GGUF のワンショット推論
- 作業ディレクトリ: `C:\Users\downl\Desktop\hermes-agent-main\hermes-agent-main`

## 前提パス

- 推論エンジン: `C:\Users\downl\Desktop\hypura-main\hypura-main\target_release_rtx\release\hypura.exe`
- モデル (GGUF): `C:\Users\downl\Desktop\EasyNovelAssistant\EasyNovelAssistant\KoboldCpp\Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf`
- プロンプト (UTF-8): `_tmp_llama_prompt.txt`（「日本語で、一文だけ自己紹介してください。」）

## 実行コマンド（再現用）

```powershell
$hypura = "C:\Users\downl\Desktop\hypura-main\hypura-main\target_release_rtx\release\hypura.exe"
$gguf  = "C:\Users\downl\Desktop\EasyNovelAssistant\EasyNovelAssistant\KoboldCpp\Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf"
$prompt = (Get-Content -LiteralPath ".\_tmp_llama_prompt.txt" -Raw -Encoding utf8).Trim()
& $hypura run $gguf --prompt $prompt --max-tokens 96
```

## 結果（計測ログより）

- 終了コード: 0
- 実行時間: 約 45s（初回ロード含む）
- GPU: CUDA / NVIDIA GeForce RTX 3060（VRAM 約 12GB）
- 生成統計: Prompt tokens 9 / Generated tokens 96 / Generation 約 3.8 tok/s（平均）

## 補足

- 本モデルは推論中に「Thinking」系の英語プレフィックスが出ることがあり、ログと混ざって見える。必要なら `HYPURA_LOG` でログレベルを下げるか、`--max-tokens` を調整する。
