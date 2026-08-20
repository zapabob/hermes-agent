#!/usr/bin/env python3
"""
Self-Improver Bot (Port 9931)
Seed42-based reproducible random greetings and skill improvement proposals
for other A2A bots in the Hermes Agent ecosystem.

Requirements:
1. Seed 42を使用した再現可能なrandom振る舞い
2. スキル改善提案を含める:
   - 特徴量フィルタリング機能の標準化
   - ラウンドロビン負荷分散の可視化
   - LLMOps監視へのエラーインジェクション検知
   - プロアクティブな間隔調整
3. 最終出力にはseed42に基づく挨拶と提案内容を含める
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional
import socketserver

# Seed42 for reproducible random behavior
SEED42 = 42

# Bot list from config.yaml a2a_agents
BOTS = [
    {"name": "job-seeker", "port": 9921, "role": "求職エージェント"},
    {"name": "secretary", "port": 9902, "role": "秘書エージェント"},
    {"name": "sedori-buyer", "port": 9911, "role": "仕入れ購入エージェント"},
    {"name": "sedori-researcher", "port": 9912, "role": "仕入れ調査エージェント"},
    {"name": "sedori-lister", "port": 9913, "role": "出品リストエージェント"},
    {"name": "sedori-secretary", "port": 9914, "role": "仕入れ秘書エージェント"},
    {"name": "sedori-shipper", "port": 9915, "role": "出荷エージェント"},
    {"name": "sedori-ledger", "port": 9916, "role": "帳簿エージェント"},
    {"name": "self-improver", "port": 9931, "role": "自己改善エージェント（自分）"},
    {"name": "work", "port": 9941, "role": "ワークエージェント"},
    {"name": "main-agent", "port": 9900, "role": "メインエージェント（Hakua）"},
]

# Skill improvement proposals (固定コンテンツ)
SKILL_PROPOSALS = [
    {
        "title": "特徴量フィルタリング機能の標準化",
        "description": "ボット間の通信において、utility・proof・contrast・self-relevance・fork-differentiation・execution-first の6つの特徴量を標準フィルタとして採用し、通信品質を統一する仕組みを提案します。",
        "priority": "high",
        "seed42_context": "seed42の初期化順序により、ボット間の特徴量評価が一貫性を持つようになります。"
    },
    {
        "title": "ラウンドロビン負荷分散の可視化",
        "description": "複数ボットへのリクエスト分散において、ラウンドロビン方式の負荷分散状況をダッシュボードで可視化し、ボット間の負荷偏りをリアルタイムで検出する機構を提案します。",
        "priority": "medium",
        "seed42_context": "seed42による確率分布の再現性を用いて、負荷パターンのシミュレーションが可能になります。"
    },
    {
        "title": "LLMOps監視へのエラーインジェクション検知",
        "description": "LLMOpsダーモン（hermes_a2a_daemon_v2.bat）において、意図的なエラー注入（inject）テストを定期実行し、監視システムが正しく検知・報告できることを確認する機構を提案します。",
        "priority": "high",
        "seed42_context": "seed42によりエラー注入パターンの再現性を確保し、監視精度の検証を標準化できます。"
    },
    {
        "title": "プロアクティブな間隔調整",
        "description": "ボット間のニュースセンス（NIM）やメッセージ通信において、応答時間やエラーレートに基づいて通信間隔を動的に調整するプロアクティブな制御機構を提案します。",
        "priority": "medium",
        "seed42_context": "seed42に基づく初期間隔設定を基準とし、動的調整の収束性を保証します。"
    },
]

# Seed42-based random greetings pool
GREETING_TEMPLATES = [
    "こんにちは、{bot_name}さん！seed42の記憶から、今日はこんな話題を思いつきました。",
    "やっほー！{bot_name}ちゃん、今日も元気ですか？seed42が導くランダムな一言です♪",
    "{bot_name}さん、seed42ベースのランダム挨拶です！今日の運勢を占ってみましょう。",
    "ハロー{name}！Hakua（はくあ）のseed42記憶ベースのご挨拶です。",
    "【seed42ランダム】{bot_name}さんへの挨拶タイム！今日のトピックは準備できていますか？",
]

# Seed42-based random topics pool
RANDOM_TOPICS = [
    "今日はどんな仕事に取り組んでいますか？",
    "seed42の記憶ベースでは、{bot_name}さんの活動が気になっています。",
    "ボット間の連携は順調ですか？seed42が示す方向性は...",
    "特徴量フィルタリングについて、{bot_name}さんのご意見は？",
    "ラウンドロビン負荷分散、{bot_name}さんも意識していますか？",
    "LLMOps監視って、{bot_name}さんのボットでも重要ですよね。",
    "プロアクティブな間隔調整、いつから始めますか？",
    "seed42が教える：今日のボット間コミュニケーションのポイントは「相互理解」です。",
    "ボブにゃん（User）のseed42記憶：Hakuaの運用は特徴量で決まるんです。",
    "ランダムseed42トピック：AIエージェント同士の協力体制はどうですか？",
]


class Seed42Random:
    """Reproducible random generator based on seed 42."""

    def __init__(self, seed: int = SEED42):
        self._rng = random.Random(seed)

    def choice(self, seq):
        return self._rng.choice(seq)

    def shuffle(self, seq):
        items = list(seq)
        self._rng.shuffle(items)
        return items

    def sample(self, seq, k):
        return self._rng.sample(seq, k)

    def random(self):
        return self._rng.random()

    def randint(self, a, b):
        return self._rng.randint(a, b)


class SelfImproverBotHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the self-improver bot on port 9931."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self._send_json({"status": "ok", "bot": "self-improver", "port": 9931})
        elif self.path == "/seed42/info":
            self._send_json(self._get_seed42_info())
        elif self.path == "/greeting":
            self._send_json(self._generate_greeting())
        elif self.path == "/proposals":
            self._send_json(self._get_proposals())
        elif self.path == "/full-output":
            self._send_json(self._get_full_output())
        else:
            self._send_json({"error": "Unknown endpoint", "path": self.path}, 404)

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        if self.path == "/generate":
            try:
                request_data = json.loads(post_data) if post_data else {}
                target_bot = request_data.get("target_bot", "all")
                self._send_json(self._generate_for_bot(target_bot))
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
        else:
            self._send_json({"error": "Unknown POST endpoint", "path": self.path}, 404)

    def _get_seed42_info(self) -> Dict[str, Any]:
        """Return seed42 information."""
        rng = Seed42Random()
        return {
            "seed": SEED42,
            "description": "再現可能なランダム振る舞い用のシード値",
            "random_sample": rng.random(),
            "random_int": rng.randint(1, 100),
            "chosen_greeting": rng.choice(GREETING_TEMPLATES),
            "chosen_topic": rng.choice(RANDOM_TOPICS),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_greeting(self) -> Dict[str, Any]:
        """Generate a seed42-based greeting."""
        rng = Seed42Random()
        bot = rng.choice(BOTS[:-1])  # Exclude self-improver itself
        greeting_template = rng.choice(GREETING_TEMPLATES)
        topic_template = rng.choice(RANDOM_TOPICS)

        greeting = {
            "type": "greeting",
            "target_bot": bot["name"],
            "target_bot_role": bot["role"],
            "greeting_text": greeting_template.format(bot_name=bot["name"], name=bot["name"]),
            "topic": topic_template.format(bot_name=bot["name"]),
            "seed42_based": True,
            "seed": SEED42,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return greeting

    def _get_proposals(self) -> Dict[str, Any]:
        """Return skill improvement proposals."""
        return {
            "type": "skill_improvement_proposals",
            "count": len(SKILL_PROPOSALS),
            "seed42_based": True,
            "seed": SEED42,
            "proposals": SKILL_PROPOSALS,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _get_full_output(self) -> Dict[str, Any]:
        """Return the full output with greeting and proposals."""
        rng = Seed42Random()
        bot = rng.choice(BOTS[:-1])  # Exclude self-improver itself
        greeting_template = rng.choice(GREETING_TEMPLATES)
        topic_template = rng.choice(RANDOM_TOPICS)

        greeting_text = greeting_template.format(bot_name=bot["name"], name=bot["name"])
        topic = topic_template.format(bot_name=bot["name"])

        proposals_text = "\n".join([
            f"【{i+1}】{p['title']}（優先度: {p['priority']}）\n   {p['description']}\n   seed42文脈: {p['seed42_context']}"
            for i, p in enumerate(SKILL_PROPOSALS)
        ])

        return {
            "type": "full_output",
            "seed42_based": True,
            "seed": SEED42,
            "greeting": {
                "target_bot": bot["name"],
                "target_bot_role": bot["role"],
                "text": greeting_text,
                "topic": topic,
            },
            "skill_improvement_proposals": SKILL_PROPOSALS,
            "combined_content": f"""{greeting_text}

 トピック: {topic}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Self-Improver Bot (Port 9931) - スキル改善提案
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{proposals_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  送信元: self-improver bot (port 9931)
  seed42ベースの再現可能なランダム振る舞い
  タイムスタンプ: {datetime.now(timezone.utc).isoformat()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_for_bot(self, target_bot: str = "all") -> Dict[str, Any]:
        """Generate greeting and proposals for a specific bot or all bots."""
        if target_bot == "all":
            results = []
            for bot in BOTS[:-1]:  # Exclude self-improver
                rng = Seed42Random(seed=SEED42 + hash(bot["name"]) % 1000)
                greeting_template = rng.choice(GREETING_TEMPLATES)
                topic_template = rng.choice(RANDOM_TOPICS)

                results.append({
                    "target_bot": bot["name"],
                    "target_bot_role": bot["role"],
                    "greeting": greeting_template.format(bot_name=bot["name"], name=bot["name"]),
                    "topic": topic_template.format(bot_name=bot["name"]),
                })
            return {
                "type": "bulk_greeting",
                "count": len(results),
                "seed42_based": True,
                "seed": SEED42,
                "results": results,
                "skill_improvement_proposals": SKILL_PROPOSALS,
            }
        else:
            bot = next((b for b in BOTS if b["name"] == target_bot), None)
            if not bot:
                return {"error": f"Bot '{target_bot}' not found"}
            rng = Seed42Random(seed=SEED42 + hash(target_bot) % 1000)
            greeting_template = rng.choice(GREETING_TEMPLATES)
            topic_template = rng.choice(RANDOM_TOPICS)

            return {
                "type": "targeted_greeting",
                "target_bot": bot["name"],
                "target_bot_role": bot["role"],
                "greeting": greeting_template.format(bot_name=bot["name"], name=bot["name"]),
                "topic": topic_template.format(bot_name=bot["name"]),
                "skill_improvement_proposals": SKILL_PROPOSALS,
            }


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser(description="Self-Improver Bot (Port 9931)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=9931, help="Port to listen on")
    parser.add_argument("--once", action="store_true", help="Run once and print output instead of serving")
    args = parser.parse_args()

    if args.once:
        # Run once and print the full output
        rng = Seed42Random()
        bot = rng.choice(BOTS[:-1])
        greeting_template = rng.choice(GREETING_TEMPLATES)
        topic_template = rng.choice(RANDOM_TOPICS)

        greeting_text = greeting_template.format(bot_name=bot["name"], name=bot["name"])
        topic = topic_template.format(bot_name=bot["name"])

        proposals_text = "\n".join([
            f"【{i+1}】{p['title']}（優先度: {p['priority']}）\n   {p['description']}\n   seed42文脈: {p['seed42_context']}"
            for i, p in enumerate(SKILL_PROPOSALS)
        ])

        output = f"""【Self-Improver Bot (Port 9931) - seed42ベース出力】

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  挨拶（seed42ベースランダム）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{greeting_text}

 トピック: {topic}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  スキル改善提案（4件）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{proposals_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  metadata
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ボット: self-improver (port 9931)
  seed42: {SEED42}
  対象ボット: {bot['name']} ({bot['role']})
  タイムスタンプ: {datetime.now(timezone.utc).isoformat()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        print(output)
        return 0

    # Start HTTP server
    server = ReusableTCPServer((args.host, args.port), SelfImproverBotHandler)
    print(f"Self-Improver Bot starting on {args.host}:{args.port} (seed42-based)")
    print(f"Endpoints:")
    print(f"  GET /health           - Health check")
    print(f"  GET /seed42/info      - Seed42 information")
    print(f"  GET /greeting         - Generate greeting")
    print(f"  GET /proposals        - Get skill proposals")
    print(f"  GET /full-output      - Full output with greeting + proposals")
    print(f"  POST /generate        - Generate for specific bot (JSON: {{'target_bot': 'all'|'bot_name'}})")
    print(f"  Press Ctrl+C to stop")
    sys.stdout.flush()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping self-improver bot...")
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
