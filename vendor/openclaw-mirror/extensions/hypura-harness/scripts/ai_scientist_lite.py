"""
AI Scientist Lite — 失敗パターン分析・改善仮説生成デーモン。

redis:atlas:failures から失敗記録を読み込み、llama-server で
改善仮説 (fitness_hint) を生成して redis:shinka:fitness_hints に保存する。
ShinkaEvolve がこのヒントを使って進化方向を調整する。

デフォルト実行間隔: 1 時間 (AI_SCIENTIST_INTERVAL_SEC)
"""
from __future__ import annotations

import json
import logging
import os
import re
import time

import requests
import redis as redis_lib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
LLAMA_URL = os.getenv("LLAMA_URL", "http://llama-service:8000")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q8_0.gguf")
INTERVAL_SEC = int(os.getenv("AI_SCIENTIST_INTERVAL_SEC", "3600"))
MAX_FAILURES_PER_RUN = int(os.getenv("AI_SCIENTIST_MAX_FAILURES", "20"))
MAX_HINTS_STORED = int(os.getenv("AI_SCIENTIST_MAX_HINTS", "100"))

_SYSTEM_PROMPT = """\
You are a research scientist analyzing coding task failures.
Given a list of failed coding task records, generate 3 concrete hypotheses \
for improving code generation quality.

Each hypothesis must include:
- "hypothesis": a clear description of what pattern causes failures
- "fitness_hint": a short actionable directive for the code optimizer (max 100 chars)

Return ONLY a JSON array. Example:
[
  {"hypothesis": "Tasks fail when...", "fitness_hint": "Add error handling for edge cases"},
  {"hypothesis": "Recursion causes...", "fitness_hint": "Prefer iterative over recursive solutions"},
  {"hypothesis": "Missing imports...", "fitness_hint": "Always include necessary import statements"}
]"""


def _parse_redis_url(url: str) -> dict:
    url = url.removeprefix("redis://")
    host, _, port = url.partition(":")
    return {"host": host or "redis", "port": int(port or 6379)}


class AiScientistLite:
    def __init__(self) -> None:
        cfg = _parse_redis_url(REDIS_URL)
        self._redis = redis_lib.Redis(**cfg, decode_responses=True)

    def run(self) -> None:
        logger.info(
            "AI Scientist Lite starting (interval=%ds, model=%s)",
            INTERVAL_SEC, LLAMA_MODEL,
        )
        while True:
            try:
                self._run_cycle()
            except Exception as e:
                logger.error("Scientist cycle error: %s", e)
            logger.info("Next analysis in %d seconds", INTERVAL_SEC)
            time.sleep(INTERVAL_SEC)

    def _run_cycle(self) -> None:
        failures = self._collect_failures()
        if not failures:
            logger.info("No failure data available, skipping cycle")
            return

        logger.info("Analyzing %d failure records...", len(failures))
        hypotheses = self._generate_hypotheses(failures)
        if hypotheses:
            self._store_hints(hypotheses)
            logger.info("Stored %d fitness hints in Redis", len(hypotheses))
        else:
            logger.warning("No hypotheses generated this cycle")

    def _collect_failures(self) -> list[dict]:
        """最新の失敗記録を Redis から取得する。"""
        raw_list = self._redis.lrange("atlas:failures", -MAX_FAILURES_PER_RUN, -1)
        failures = []
        for raw in raw_list:
            try:
                failures.append(json.loads(raw))
            except json.JSONDecodeError:
                pass
        return failures

    def _generate_hypotheses(self, failures: list[dict]) -> list[dict]:
        """llama-server で失敗パターンから改善仮説を生成する。"""
        # 失敗記録をコンパクトに整形
        failure_summary = [
            {
                "prompt_snippet": f.get("prompt", "")[:100],
                "stop_reason": f.get("stop_reason", ""),
                "error": f.get("error", "")[:200],
            }
            for f in failures
        ]

        try:
            resp = requests.post(
                f"{LLAMA_URL}/v1/chat/completions",
                json={
                    "model": LLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps(failure_summary, ensure_ascii=False),
                        },
                    ],
                    "temperature": 0.7,
                    "max_tokens": 512,
                },
                timeout=120,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return self._parse_hypotheses(content)
        except Exception as e:
            logger.error("Failed to generate hypotheses: %s", e)
            return []

    def _parse_hypotheses(self, content: str) -> list[dict]:
        """LLM レスポンスから JSON 配列を抽出する。"""
        # JSON ブロック抽出を試みる
        for pattern in [r"```json\n?(.*?)```", r"```\n?(.*?)```", r"(\[.*?\])"]:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if isinstance(data, list):
                        return [
                            h for h in data
                            if isinstance(h, dict) and "fitness_hint" in h
                        ]
                except json.JSONDecodeError:
                    pass

        # フォールバック: 直接パース
        try:
            data = json.loads(content.strip())
            if isinstance(data, list):
                return [h for h in data if isinstance(h, dict) and "fitness_hint" in h]
        except json.JSONDecodeError:
            pass

        logger.warning("Could not parse hypotheses from LLM response")
        return []

    def _store_hints(self, hypotheses: list[dict]) -> None:
        """fitness_hint を redis:shinka:fitness_hints に保存する。"""
        for h in hypotheses:
            hint = h.get("fitness_hint", "").strip()
            if hint:
                self._redis.rpush("shinka:fitness_hints", hint)
                logger.debug("Stored hint: %s", hint)
        # 最大 MAX_HINTS_STORED 件のみ保持
        self._redis.ltrim("shinka:fitness_hints", -MAX_HINTS_STORED, -1)


if __name__ == "__main__":
    AiScientistLite().run()
