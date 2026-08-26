from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "hermes-comparison-20260727"
OUT.mkdir(parents=True, exist_ok=True)

slides = [
    ("Hermes Agent\n比較動画", "NousResearch/hermes-agent  vs  zapabob/hermes-agent-windows", "比較対象は各リポジトリの記録済みコミット"),
    ("上流版: NousResearch", "標準のHermes Agent基盤", "CLI / Gateway / Desktop / Browser / Skills\nシンプルで追従しやすい上流実装"),
    ("fork版: zapabob", "個人環境向けの拡張レイヤー", "TTS・X投稿・記憶・VRChat・Windows運用\n外部ツールとローカル自動化を統合"),
    ("違いの核心", "基盤  vs  統合", "上流版: 安定した標準基盤\nfork版: 使う環境に合わせた自動化と運用拡張"),
    ("使い分け", "どちらを選ぶ?", " upstream: 素のHermesを追いたい人\n fork: はくあの音声・記憶・運用を一体化したい人"),
    ("まとめ", "どちらもHermes Agentが土台", "fork固有機能は上流へ自動反映されません\n用途と保守方針に合わせて選ぶのが正解"),
]

commits = {
    "NousResearch/hermes-agent": "339d968689a3b91c5f537d7198ff28abde32ab3b",
    "zapabob/hermes-agent-windows": "e1c6cf36fcc419923520720a2a05720a0282174f",
}

def font(size: int, bold: bool = False):
    candidates = [
        Path("C:/Windows/Fonts/meiryob.ttc" if bold else "C:/Windows/Fonts/meiryo.ttc"),
        Path("C:/Windows/Fonts/yu gothic bold.ttf" if bold else "C:/Windows/Fonts/yu gothic medium.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()

# Render directly with Pillow so the build does not depend on ImageMagick.
for i, (title, subtitle, body) in enumerate(slides, 1):
    im = Image.new("RGB", (1920, 1080), (17, 24, 39))
    draw = ImageDraw.Draw(im)
    for y in range(1080):
        t = y / 1080
        draw.line((0, y, 1920, y), fill=(int(17 + 32*t), int(24 + 22*t), int(39 + 70*t)))
    draw.ellipse((1420, -100, 1980, 460), fill=(70, 64, 150))
    draw.ellipse((-220, 760, 480, 1460), fill=(20, 70, 100))
    draw.text((120, 105), "HERMES AGENT / HAKUA COMPARISON", font=font(28, True), fill=(165, 180, 252))
    title_lines = title.split("\\n")
    for n, line in enumerate(title_lines):
        draw.text((120, 280 + n*100), line, font=font(82, True), fill="white")
    draw.text((120, 510), subtitle, font=font(40), fill=(196, 181, 253))
    for n, line in enumerate(body.split("\\n")):
        draw.text((120, 610 + n*64), line, font=font(38), fill=(224, 231, 255))
    draw.text((120, 980), "NousResearch/hermes-agent  ×  zapabob/hermes-agent-windows", font=font(24), fill=(148, 163, 184))
    draw.text((1770, 980), f"{i:02d}/06", font=font(24), fill=(148, 163, 184), anchor="ra")
    im.save(OUT / f"slide-{i:02d}.png")

script = OUT / "narration.txt"
script.write_text("今回はNousResearch版の最新Hermes Agentと、zapabob版を比較します。比較時点は、NousResearch版が339d968、zapabob版がe1c6cf3です。NousResearch版は上流の標準基盤。一方zapabob版は、TTS、X投稿、記憶、Windows運用、外部ツール連携など、個人環境向けの統合レイヤーを追加しています。安定した基盤を重視するなら上流版、個人環境への統合と自動化を重視するならzapabob版が向いています。ただし、fork固有の変更は上流へ自動反映されません。", encoding="utf-8")

manifest = {"out": str(OUT), "slides": len(slides), "narration": str(script), "akari_video_enabled": True, "commits": commits, "comparison_note": "Snapshot comparison; fork changes include integrations, docs, configuration, and operational files."}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(manifest, ensure_ascii=False))
subprocess.run(["ffmpeg", "-y", "-framerate", "1/3", "-i", str(OUT / "slide-%02d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(OUT / "slides-silent.mp4")], check=True)
print(OUT)
