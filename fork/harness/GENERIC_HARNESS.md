# Generic Agent Harness — 自立成長基盤

> **位置づけ**: このリポジトリは `NousResearch/hermes-agent` を upstream としつつ、
> **NousResearch にランタイム依存しない汎用AIエージェントハーネス** および
> **Windows汎用AIワークステーション基盤** として自立成長する。
> upstream の開発が停止または行き詰まるまで追従し、以後は完全自立へ移行する。

## ハーネス定義

**ハーネス (Harness)** = エージェントの「狭い腰」

- Core: `run_agent.py` / `gateway/` / `tool registry` / `model_tools.py` — 薄く保つ
- Edges: `plugins/` `skills/` `downstream/` `fork/extensions/` — 能力はここで拡張
- 新ツールは Footprint Ladder に従い、core への直追加は最終手段

汎用性は **42プロバイダ / 22プラットフォーム / 9メモリ / 11検索** が
同一ハーネス上で差し替え可能であることで担保される。特定プロバイダ（Nous含む）への
ハード依存は持たない。

## Windows ワークステーション基盤

```
Watchdog Go ──→ Desktop/Electron ──→ Gateway ──→ Agent Core
     ├─→ llama.cpp / GGUF (local inference)
     ├─→ Embedding loopback (semantic search)
     ├─→ VOICEVOX / Irodori (voice)
     └─→ VRChat / Unity (embodiment)
              ↕
        Ebbinghaus + SemanticGraph + Obsidian (memory)
```

このスタック自体が「汎用AIワークステーション」のリファレンス実装。
詳細は `fork/operations/` `fork/extensions/` `WINDOWS_PLATFORM_CONTRACT.md` を参照。

## Upstream 政策

| ファイル | 役割 |
|---------|------|
| `scripts/merge_tools/hermes-merge-conflict-strategies.json` | パス別マージ政策 |
| `scripts/sync_all.py` | 同期オーケストレータ |
| `.codex/UPSTREAM_SNAPSHOT.json` | 凍結SHA（移動追従禁止） |
| `UPSTREAM_ADOPTION.yaml` / `CARRY.yaml` | 採用分類 / 直接carry追跡 |

```powershell
py -3 scripts/sync_all.py --dry-run                          # 分類確認
py -3 scripts/sync_all.py --merge --target main --allow-preflight-blockers  # 実行
py -3 scripts/merge_tools/apply_post_merge_overlay.py --upstream-ref upstream/main --old-head $preMergeSha
```

`upstream` / `preserve_custom` / `official_with_overlay` / `manual_api_followup` の
4分類を厳守。`toolsets.py` は overlay sanitizer 経由のみで解決。

## 成長原則

1. **Nous は開発元、依存先ではない** — fetch のみ、ランタイム依存ゼロ
2. **Core は薄く、Edges で伸ばす** — Plugin/Skill 優先
3. **Windows は Tier-1** — ネイティブ検証なしの機能は未検証扱い
4. **停止まで追従、停止後は自立** — 90日無更新 or アーキテクチャ行き詰まりで凍結判定

## 関連文書

- `_docs/2026-09-03_generic-harness-independence.md` — 自立化方針の完全版
- `fork/README.md` — フォーク全体像
- `fork/harness/AGENTS.md` — マージ時のエージェント手順
- `.codex/WINDOWS_PLATFORM_CONTRACT.md` — Windows 契約の正本
