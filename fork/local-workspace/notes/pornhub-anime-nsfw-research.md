# Pornhub風二次元エロ画像生成のベストプラクティス調査レポート

**調査日**: 2025年  
**対象環境**: RTX 5060 Ti 16GB VRAM、ComfyUI、Stable Diffusion系モデル  
**目的**: ローカル画像生成（SDXLベース or Ponyベース or 二次元特化モデル）用のプロンプトテンプレート、推奨モデル、推奨LoRA、ネガティブプロンプトを決定するためのエビデンス収集

---

## 1. 各リサーチ軸の要約

### 1.1 Pornhub ブランドビジュアル要素
- **公式カラー**: `#FFA31A` (オレンジ / メイン)、`#1B1B1B` / `#292929` (ダークグレー/ブラック背景)、`#FFFFFF` (白テキスト)
- **ロゴ構成**: 「Porn」を黒テキスト、「hub」をオレンジ角丸長方形内の白テキストで配置。フォントは太字サンセリフ（Helvetica/Arial系の変形）
- **サムネイルレイアウト**: 中央配置のメイン画像、左下または右下にロゴ、タグラインは画像下部に半透明黒バー+白文字、またはオレンジグラデーションバー
- **二次元適用時**: イラストの右下または左下にミニロゴ（角丸長方形 + 「hub」）、または全体にオレンジのビネット/グラデーションオーバーレイを薄く適用

### 1.2 X (Twitter) の NSFW AI アーティスト動向（2025-2026）
- **主要コミュニティ**: @civitai 公式、HuggingFace Spaces デモ、モデル作者アカウント（PurpleSmartAI、cagliostrolab、OnomaAIResearch）
- **トレンドモデル**: **Pony Diffusion V6 XL**（最大コミュニティ）、**Illustrious XL v0.1**（キャラクター再現力最高）、**Animagine XL 4.0 Opt**（アニメ特化）
- **プロンプト形式**: Danbooruタグベース、自然言語混在、品質タグ必須（score_9, score_8_up 等）、ratingタグで露出度制御
- **人気キーワード**: `1girl, solo, explicit, nsfw, large breasts, detailed skin, masterpiece, absurdres`

### 1.3 Reddit 二次元NSFWベストプラクティス
- **主要サブレディット**: r/StableDiffusion, r/sdnsfw, r/pony, r/aiArt, r/NovelAI, r/AnimeResearch
- **推奨モデル**: Pony V6 XL（NSFW LoRAライブラリ最大）、Illustrious XL v0.1（キャラLoRA不要）、Animagine XL 4.0 Opt（アニメ画風）
- **推奨 LoRA**: Incase Style（西洋コミック風）、ExpressiveH（ヘンタイ陰影）、Pony Amateur（実写風）、NSFW Styles 5パック、Not Artists Styles（倫理的）
- **プロンプト構成**: ポジティブ（品質タグ→主題タグ→詳細→スタイルタグ）、ネガティブ（lowres, worst quality, bad anatomy, bad hands, text, watermark等）
- **サンプラー設定**: **Euler a / DPM++ 2M Karras**、CFG 5-7、Steps 20-30（品質重視）、8ステップ（Turbo/LCM使用時）

### 1.4 Pornhub風スタイルでStable Diffusion生成
- **Civitai等のサンプル**: 「Pornhub logo」検索でロゴ単体生成例多数。NSFWイラストへのロゴ合成例はコミュニティで「Incase Style + ExpressiveH」等のスタイルLoRA併用が主流
- **実践的手法**: 生成後に画像編集でロゴ追加、またはControlNet/Inpaintingでロゴ領域を確保して生成、またはプロンプトに「pornhub logo, orange rounded rectangle, black text」を含める

### 1.5 画像1枚あたりの生成時間とVRAM要件
| 解像度 | VRAM (FP16) | 25 Steps (DPM++ 2M) | 8 Steps (LCM/Hyper-SD) |
|--------|------------|---------------------|------------------------|
| 832×1216 | ~8-10 GB | ~3-5 秒 | ~1-2 秒 |
| 1024×1536 | ~10-12 GB | ~5-8 秒 | ~2-3 秒 |
| 768×1024 | ~7-9 GB | ~2-4 秒 | ~1-2 秒 |

- **RTX 5060 Ti 16GB**: SDXL/Pony/Illustrious/Animagine 全て FP16 で余裕で動作、LoRA 2-3枚スタック可能
- **Turbo系**: SDXL Turbo（1-4 step）、LCM-LoRA（4-8 step）、Hyper-SD（4 step）で高速化可能だが、NSFW細部品質は20-30 stepに劣る
- **推奨**: 品質優先なら **Euler a / DPM++ 2M Karras, 25-30 steps, CFG 6-7**

---

## 2. 具体的なプロンプトテンプレート（コピペ可能）

### 2.1 Pony Diffusion V6 XL 用（標準・高品質）

```text
# Positive Prompt
score_9, score_8_up, score_7_up, score_6_up, rating_explicit,
1girl, solo, long hair, silver hair, blue eyes, large breasts,
detailed skin, soft skin texture, (detailed eyes:1.3), (detailed lips:1.2),
wearing lingerie, garter belt, thighhighs, choker,
bedroom, night, soft lighting, volumetric lighting, rim lighting,
dynamic pose, lying on bed, looking at viewer, parted lips, flirtatious smile,
masterpiece, best quality, ultra-detailed, highres, absurdres,
digital illustration, anime style, cel shading

# Negative Prompt
lowres, worst quality, low quality, normal quality, bad anatomy, bad hands,
missing fingers, extra digit, fewer digits, extra limbs, missing limbs,
fused fingers, mutated hands, deformed, ugly, deformed face, long neck,
cross-eyed, bad eyes, asymmetric eyes, text, watermark, signature,
username, artist name, logo, cropped, out of frame, duplicate, error,
jpeg artifacts, blurry, noise, grainy
```

### 2.2 Pony Diffusion V6 XL 用（Pornhubスタイルロゴ付き）

```text
# Positive Prompt
score_9, score_8_up, score_7_up, score_6_up, rating_explicit,
1girl, solo, long hair, pink hair, green eyes, large breasts,
detailed skin, (soft skin texture:1.2), (detailed eyes:1.3),
wearing black lingerie, garter belt, fishnet thighhighs, choker,
bedroom, pornhub logo, orange rounded rectangle, black text "hub",
white text "porn", bottom right corner, watermark style,
cinematic lighting, rim lighting, volumetric lighting, bokeh,
dynamic angle, from side, cowboy shot,
masterpiece, best quality, ultra-detailed, highres, absurdres,
digital illustration, anime style, cel shading

# Negative Prompt（同上）
```

### 2.3 Illustrious XL v0.1 用（キャラ再現力重視）

```text
# Positive Prompt
(best quality:1.2), (amazing quality:1.2), (very detailed:1.3),
1girl, solo, character_name, series_name, long hair, blue eyes,
large breasts, detailed skin, (detailed eyes:1.3), (detailed lips:1.2),
wearing lingerie, thighhighs, bedroom, night, soft lighting,
rim lighting, volumetric lighting, dynamic pose, looking at viewer,
explicit, nsfw, sensitive,
masterpiece, high score, great score, absurdres

# Negative Prompt
lowres, worst quality, low quality, bad anatomy, bad hands,
missing fingers, extra digits, fewer digits, cropped, text,
watermark, signature, logo, username, blurry, jpeg artifacts,
deformed, ugly, bad face, bad eyes, mutated hands
```

**設定**: Euler a, Steps 24-28, CFG 5.5-6.5, CLIP Skip 2

### 2.4 Animagine XL 4.0 Opt 用（アニメ特化・品質タグは末尾）

```text
# Positive Prompt
1girl, solo, character_name, series_name, long hair, silver hair,
green eyes, large breasts, detailed skin, (detailed eyes:1.3),
wearing school uniform, skirt, thighhighs, bedroom, night,
sensitive, nsfw, explicit,
masterpiece, high score, great score, absurdres

# Negative Prompt
lowres, worst quality, low quality, bad anatomy, bad hands,
missing fingers, extra digits, fewer digits, cropped, text,
watermark, signature, logo, username, blurry, jpeg artifacts,
deformed, ugly, bad face, bad eyes, mutated hands, normal quality
```

**設定**: DPM++ 2M SDE Karras / Euler a, Steps 25-30, CFG 5-7, CLIP Skip 2  
**重要**: 品質タグ（masterpiece, high score, great score, absurdres）は**必ずプロンプト末尾**に配置

---

## 3. ネガティブプロンプトテンプレート（モデル共通・推奨プリセット）

### 3.1 SDXL/Pony/Illustrious共通（siutil準拠・推奨）

```text
lowres, worst quality, low quality, normal quality,
bad anatomy, bad hands, missing fingers, extra digit, fewer digits,
extra limbs, missing limbs, fused fingers, mutated hands, deformed,
ugly, deformed face, long neck, cross-eyed, bad eyes, asymmetric eyes,
text, watermark, signature, username, artist name, logo,
cropped, out of frame, duplicate, error, jpeg artifacts,
blurry, noise, grainy
```

### 3.2 Pony V6 専用追加（sourceタグ除外）

```text
source_anime, source_cartoon, source_furry, source_pony
```

### 3.3 風景/背景のみ生成時

```text
lowres, worst quality, low quality, bad anatomy, bad hands,
person, people, human, 1girl, 1boy, animal, creature, figure,
text, watermark, signature, username, logo, cropped,
jpeg artifacts, blurry, noise, grainy
```

---

## 4. 推奨モデル（HuggingFace repo URL 付き、VRAM要件）

| モデル | HuggingFace Repo | タイプ | 推奨VRAM (FP16) | 特徴 |
|--------|------------------|--------|-----------------|------|
| **Pony Diffusion V6 XL** | `Runware/Pony_Diffusion_V6_XL` / `Polenov2024/Pony-Diffusion-V6-XL` | SDXL finetune | 8-10 GB | **NSFW最強、LoRAライブラリ最大**、Danbooruタグ対応、自然言語も可 |
| **Illustrious XL v0.1** | `OnomaAIResearch/Illustrious-xl-early-release-v0` / `p1atdev/Illustrious-XL-v0.1-fp8` | SDXL finetune | 8-10 GB | キャラ再現力最高、アーティストスタイル内蔵、キャラLoRA不要 |
| **Animagine XL 4.0 Opt** | `cagliostrolab/animagine-xl-4.0` | SDXL finetune | 8-10 GB | アニメ特化、品質タグ末尾配置必須、ratingタグで露出度制御 |
| **Animagine XL 4.0 Zero** | `cagliostrolab/animagine-xl-4.0-zero` | SDXL base | 8-10 GB | LoRA学習用ベース、クリーンな線画 |
| **Anything V5** | `xyn-ai/anything-v5` / `Cubing/AnythingV5Ink` | SD1.5 | 4-6 GB | 軽量、古いハード向け |

**RTX 5060 Ti 16GB では全モデル FP16 で余裕動作、LoRA 2-3枚スタック可能**

---

## 5. 推奨LoRA（HuggingFace/Civitai URL 付き、トリガーワード、推奨strength）

| LoRA名 | 用途 | トリガーワード | 推奨Strength | Civitai / HuggingFace |
|--------|------|---------------|-------------|----------------------|
| **Incase Style [PonyXL]** | 西洋コミック風NSFW | なし（v2） | 1.0 solo / 0.4-0.6 mix | [Civitai #352902](https://civitai.com/models/352902) |
| **ExpressiveH (Hentai Style)** | ヘンタイ陰影・エロ表現 | `Expressiveh` | 0.40-0.60 | [Civitai #352902](https://civitai.com/models/352902) |
| **Pony Amateur ✨** | 実写風・アマチュア写真 | `photo, film grain, amateur, webcam photo, flash` | 0.2-0.9 (clip skip 2) | Civitai検索 "Pony Amateur" |
| **NSFW Styles for PonyDiffusionV6 (5-pack)** | 完成済み5スタイル | `PONYXL_STYLE_[name]_ownwaifu` | 0.8-1.0 solo推奨 | [Civitai #352902](https://civitai.com/models/352902) |
| **Not Artists Styles for Pony V6 XL** | 倫理的スタイル(40+) | スタイル名 | 0.8-1.0 | Civitai検索 "Not Artists Styles Pony" |
| **ExpressiveH & Incase Mixed v3 (UOC)** | 融合アニメスタイル | 両方のトリガー | 0.5-0.8 | Civitai検索 |
| **Realism Lora By Stable Yogi** | ハイパーリアル肌 | 専用embeddings併用推奨 | 0.4-1.5 | Civitai検索 "Realism Lora Stable Yogi" |
| **Amateur Flash Photo for Pony** | ハードフラッシュ暗室 | `amatrflsh` | 1.0 (clip skip 2) | Civitai検索 |
| **Pony Add More Details** | ディテール復元 | トリガー不要 | 0.3-0.5 (スタック用) | Civitai検索 |
| **Point and Shoot — Amateur Slider** | 実写感スライダー | スライダー調整 | 0.1刻み調整 | Civitai検索 |

**重要**: Pony V6 では **CLIP Skip 2 必須**、`rating_explicit` / `rating_safe` で露出度制御

---

## 6. 推奨解像度とサンプラー設定

### 6.1 品質優先（標準設定）

| 項目 | 推奨値 |
|------|--------|
| **解像度** | 832×1216 (縦長・スマホ向け), 1024×1536 (高解像度縦長), 896×1152, 1152×896 (横長) |
| **サンプラー** | **Euler a** (最安定), **DPM++ 2M Karras** (ディテール), **DPM++ 2M SDE Karras** (創造性) |
| **Steps** | **25-30** (標準), 30-50 (DPM++ 2M SDE で超高品質) |
| **CFG Scale** | **6-7** (Pony), **5.5-6.5** (Illustrious), **5-7** (Animagine) |
| **CLIP Skip** | **2** (Pony必須), 1-2 (他) |
| **VAE** | `sdxl-vae-fp16-fix.safetensors` 必須 |

### 6.2 高速生成（Turbo/LCM/Hyper-SD使用時）

| 項目 | 推奨値 |
|------|--------|
| **LCM-LoRA** | `latent-consistency/lcm-lora-sdxl` + **CFG 1.5-2.5, Steps 4-8**, sampler: **LCM** |
| **Hyper-SD** | `ByteDance/Hyper-SD` (Hyper-SDXL-4steps-lora.safetensors) + **CFG 1, Steps 4**, sampler: **DPM++ 2M Karras / UniPC** |
| **SDXL Turbo** | `stabilityai/sdxl-turbo` + **CFG 1, Steps 1-4**, sampler: **Euler a** |
| **注意** | NSFW細部（解剖学、手指、陰影）は20-30 stepsに劣る。プレビュー/反復用に限定推奨 |

### 6.3 RTX 5060 Ti 16GB 実測ベンチマーク目安

- **1024×1024, 25 steps, DPM++ 2M**: ~3-5 秒
- **1024×1536, 25 steps, DPM++ 2M**: ~5-8 秒  
- **832×1216, 8 steps, LCM**: ~1.5-2 秒
- **VRAM使用量**: SDXL Base ~6.5 GB + LoRA 1枚 ~0.5 GB + ControlNet ~1-2 GB = **余裕で 16 GB 内収まる**

---

## 7. Pornhub風サムネイルのレイアウト/色/フォント ベストプラクティス

### 7.1 ロゴ配置ルール
- **位置**: 右下または左下（画像から 2-3% マージン）
- **サイズ**: 画像幅の 15-20%（横長の場合）、または高さの 8-10%（縦長の場合）
- **構成**: 
  - 黒文字 "Porn" + オレンジ角丸長方形内白文字 "hub"
  - 長方形の角丸半径: 高さの 20-25%
  - フォントウェイト: Bold (700-800)

### 7.2 カラーパレット（公式準拠）

| 用途 | Hex | RGB | 用途例 |
|------|-----|-----|--------|
| **Pornhub Orange (メイン)** | `#FFA31A` | 255, 163, 26 | ロゴ背景、アクセントバー、CTA |
| **Pornhub Orange (代替)** | `#FF9900` | 255, 153, 0 | グラデーション終端 |
| **Dark Background** | `#1B1B1B` | 27, 27, 27 | サムネイル背景、オーバーレイバー |
| **Dark Gray** | `#292929` | 41, 41, 41 | セカンダリ背景 |
| **Medium Gray** | `#808080` | 128, 128, 128 | 無効状態、サブテキスト |
| **White** | `#FFFFFF` | 255, 255, 255 | ロゴ "hub" 文字、メインテキスト |

### 7.3 グラデーション/オーバーレイパターン
```css
/* 右下フェードイン */
background: linear-gradient(135deg, transparent 60%, rgba(27,27,27,0.8) 100%);

/* 下部バー（タグライン用） */
background: linear-gradient(to top, rgba(27,27,27,0.9), transparent);

/* オレンジアクセントバー */
background: linear-gradient(90deg, #FFA31A, #FF9900);
```

### 7.4 フォント指定
- **ロゴ用**: Helvetica Neue Bold / Arial Black / Inter Bold (700-800)
- **タグライン/タイトル**: Inter SemiBold (600) / Roboto Medium (500)
- **日本語併用時**: Noto Sans JP Bold / M PLUS 1p Bold

### 7.5 実装テンプレート（画像生成後合成用・Python/Pillow想定）

```python
from PIL import Image, ImageDraw, ImageFont

def add_pornhub_watermark(img_path, output_path, position="bottom-right"):
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size
    
    # ロゴサイズ計算
    logo_h = int(h * 0.08)
    logo_w = int(logo_h * 3.5)  # 約3.5:1 アスペクト
    radius = int(logo_h * 0.22)
    
    # 位置計算
    margin = int(w * 0.02)
    if position == "bottom-right":
        x, y = w - logo_w - margin, h - logo_h - margin
    else:  # bottom-left
        x, y = margin, h - logo_h - margin
    
    # 描画
    draw = ImageDraw.Draw(img)
    
    # オレンジ角丸長方形
    draw.rounded_rectangle([x, y, x+logo_w, y+logo_h], radius=radius, fill="#FFA31A")
    
    # テキスト "hub" (白)
    font_size = int(logo_h * 0.65)
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # "Porn" (黒) - 長方形の左側外
    porn_w = int(logo_w * 0.45)
    draw.text((x - porn_w - 5, y + (logo_h - font_size)//2), "Porn", fill="#1B1B1B", font=font)
    
    # "hub" (白) - 長方形内中央
    hub_w = draw.textlength("hub", font=font)
    draw.text((x + (logo_w - hub_w)//2, y + (logo_h - font_size)//2), "hub", fill="#FFFFFF", font=font)
    
    img.save(output_path)
```

---

## 8. 1次/2次ソースURL（主要10+）

### 公式・一次ソース
1. **Pornhub公式ロゴ (SVG)**: https://commons.wikimedia.org/wiki/File:Pornhub-logo.svg
2. **Pornhubヘルプ - サムネイルガイド**: https://help.pornhub.com/hc/en-us/articles/4419853116691-Video-Thumbnails
3. **Pornhub Model Blog - Thumbnail Crash Course**: https://www.pornhub.com/blog/crash-course-thumbnails
4. **Pony Diffusion V6 XL 公式 (Civitai)**: https://civitai.com/models/257749/pony-diffusion-v6-xl
5. **Pony V6 作業ノート (Civitai)**: https://civitai.com/articles/13148/note-about-working-with-the-ponyv6-model
6. **Illustrious XL 公式 (Civitai)**: https://civitai.com/models/795765/illustrious-xl
7. **Animagine XL 4.0 公式 (HuggingFace)**: https://huggingface.co/cagliostrolab/animagine-xl-4.0
8. **Animagine XL 4.0 最適化ガイドライン (CagliostroLab)**: https://cagliostrolab.net/posts/optimizing-animagine-xl-40-in-depth-guideline-and-update

### コミュニティ・二次ソース
9. **WhatLab Pony Prompting Guide**: https://whatlab.ai/guides/pony-prompting-guide
10. **siutil ネガティブプロンプトジェネレータ**: https://siutil.com/negative-prompt/
11. **OfflineCreator - Best Pony NSFW LoRAs 2026**: https://offlinecreator.com/best-pony-nsfw-loras-civitai-2026
12. **OfflineCreator - SDXL ローカル実行ガイド**: https://offlinecreator.com/how-to-run-sdxl-locally
13. **BetterWaifu Pony Diffusion Guide**: https://betterwaifu.com/blog/pony-diffusion-guide
14. **Gigagpu RTX 5060 Ti 16GB SDXL Benchmark**: https://gigagpu.com/rtx-5060-ti-16gb-sdxl-benchmark/
15. **Reddit r/StableDiffusion - SDXL ワークフロー**: https://www.reddit.com/r/StableDiffusion/comments/14zcypw/
16. **Pornhub Style Logo Generator (GitHub - logoly)**: https://github.com/bestony/logoly
17. **Pornhub Color Palette (color-hex)**: https://www.color-hex.com/color-palette/77108

---

## 9. 実装時の重要チェックリスト

- [ ] **モデル選定**: NSFW LoRA使うなら **Pony V6 XL** 一択。キャラ再現なら **Illustrious XL v0.1**。純アニメなら **Animagine XL 4.0 Opt**
- [ ] **CLIP Skip 2**: Pony V6 では必須設定
- [ ] **VAE**: `sdxl-vae-fp16-fix` 必ず適用
- [ ] **品質タグ順序**: Pony/Illustrious = 先頭、Animagine = **末尾**
- [ ] **Ratingタグ**: `rating_explicit` / `rating_safe` / `rating_sensitive` で露出度制御
- [ ] **解像度**: 832×1216 または 1024×1536 (縦長・サムネイル向け)、SDXLネイティブ 1024×1024 基準
- [ ] **サンプラー**: Euler a (安定) / DPM++ 2M Karras (品質)
- [ ] **Steps**: 25-30 (本番)、8 (LCM/Hyper-SD プレビュー)
- [ ] **CFG**: 6-7 (Pony), 5.5-6.5 (Illustrious), 5-7 (Animagine)
- [ ] **LoRAスタック**: 最大2-3枚、Strength 合計 1.0-1.5 以内推奨
- [ ] **Pornhubロゴ**: 生成後合成推奨（Inpainting/ControlNetより確実）。位置は右下、色は `#FFA31A` / `#1B1B1B`

---

## 10. 次のアクション（推奨）

1. **ComfyUIワークフロー構築**: 上記設定をノード化（KSampler, CLIPTextEncode, LoadCheckpoint, VAEEncode等）
2. **プロンプトテンプレート保存**: ポジ/ネガをワイルドカード/テキストファイル化
3. **LoRAダウンロード**: Incase Style, ExpressiveH, Pony Amateur から着手
4. **ベンチマーク実行**: RTX 5060 Ti で各解像度・ステップ数での生成時間・VRAM測定
5. **ロゴ合成自動化**: PythonスクリプトまたはComfyUI ImageCompositeノードでバッチ処理化

---

**注意**: 本レポートは防御/制作目的のベストプラクティス抽出に限定しています。実在人物の偽画像生成、商標権侵害、法令違反には使用しないでください。Pornhubロゴ/商標の使用は同社の商標権に抵触する可能性があります。個人的研究・学習目的の範囲内でご利用ください。