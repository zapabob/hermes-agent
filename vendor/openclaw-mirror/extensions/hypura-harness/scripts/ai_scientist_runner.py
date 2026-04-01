"""
AI Scientist Runner — SakanaAI/AI-Scientist の Slim モード統合ラッパー。

LaTeX/PDF 生成はスキップし、アイデア生成と実験実行のみを行う。
Ollama 互換: OLLAMA_BASE_URL 環境変数でエンドポイントを指定する。

Redis キー:
  atlas:failures         (LIST, 読み取り) → リサーチテーマ自動設定
  ai_scientist:findings  (LIST, 書き込み, max 200) → 発見ログ
  ai_scientist:tasks     (LIST, 読み取り) → 外部タスク投入
  shinka:fitness_hints   (LIST, 書き込み) → ShinkaEvolve 改善ヒント

デーモンモード (このファイルを直接実行した場合):
  AI_SCIENTIST_INTERVAL_SEC (default: 7200) 秒毎に run_from_failures() を実行。
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# vendor/AI-Scientist を sys.path に追加
_AI_SCIENTIST_DIR = os.environ.get(
    "AI_SCIENTIST_DIR",
    str(Path(__file__).parent.parent.parent.parent / "vendor" / "AI-Scientist"),
)
if Path(_AI_SCIENTIST_DIR).exists() and _AI_SCIENTIST_DIR not in sys.path:
    sys.path.insert(0, _AI_SCIENTIST_DIR)

REDIS_URL       = os.environ.get("REDIS_URL", "redis://localhost:6379")
_ollama_raw     = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
OLLAMA_BASE_URL = _ollama_raw if _ollama_raw.endswith("/v1") else _ollama_raw + "/v1"
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "qwen-hakua-core:latest")
INTERVAL_SEC    = int(os.environ.get("AI_SCIENTIST_INTERVAL_SEC", "7200"))
MAX_IDEAS       = int(os.environ.get("AI_SCIENTIST_MAX_IDEAS", "5"))
MAX_FINDINGS    = 200


# ── Redis ヘルパー ──────────────────────────────────────────────────────────

def _get_redis():
    try:
        import redis as redis_lib
        url = REDIS_URL.removeprefix("redis://")
        host, _, port = url.partition(":")
        r = redis_lib.Redis(host=host or "localhost", port=int(port or 6379), decode_responses=True)
        r.ping()
        return r
    except Exception as e:
        logger.debug("Redis unavailable: %s", e)
        return None


def _push_finding(r, topic: str, idea: dict, result: dict) -> None:
    record = {
        "topic": topic,
        "idea": idea,
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    r.rpush("ai_scientist:findings", json.dumps(record, ensure_ascii=False))
    r.ltrim("ai_scientist:findings", -MAX_FINDINGS, -1)


def _push_fitness_hint(r, hint: str) -> None:
    if not hint:
        return
    r.rpush("shinka:fitness_hints", hint[:100])
    r.ltrim("shinka:fitness_hints", -100, -1)


# ── AI-Scientist ラッパー ─────────────────────────────────────────────────

class AiScientistRunner:
    """SakanaAI/AI-Scientist の Slim モード (アイデア生成 + 実験、LaTeX なし)。"""

    def __init__(self) -> None:
        self._available = self._check_available()

    def _check_available(self) -> bool:
        try:
            import ai_scientist  # noqa: F401
            return True
        except ImportError:
            logger.warning(
                "ai_scientist package not found at %s. "
                "Run: powershell -File scripts/Download-Vendor.ps1 -Component AI-Scientist",
                _AI_SCIENTIST_DIR,
            )
            return False

    # ── public API ────────────────────────────────────────────────────────

    def run_ideas(
        self,
        topic: str,
        template: str = "nanoGPT",
        num_ideas: int = 3,
        model: Optional[str] = None,
    ) -> list[dict]:
        """
        AI-Scientist のアイデア生成を実行する。
        """
        if not self._available:
            return self._fallback_ideas(topic, num_ideas, model)

        try:
            return self._run_ideas_sakana(topic, template, num_ideas, model)
        except Exception as e:
            logger.warning("SakanaAI idea generation failed (%s), falling back: %s", type(e).__name__, e)
            return self._fallback_ideas(topic, num_ideas, model)

    def run_experiment(self, idea: dict, template: str = "nanoGPT", model: Optional[str] = None) -> dict:
        """
        AI-Scientist の実験実行 (perform_experiments) を呼ぶ。
        """
        if not self._available:
            return {"success": False, "error": "ai_scientist not available"}

        try:
            return self._run_experiment_sakana(idea, template, model)
        except Exception as e:
            logger.warning("SakanaAI experiment failed: %s", e)
            return {"success": False, "error": str(e)}

    def run_from_failures(self, model: Optional[str] = None) -> dict:
        """
        atlas:failures を読んでリサーチテーマを自動設定し、アイデアを生成する。
        発見を ai_scientist:findings + shinka:fitness_hints に保存する。
        """
        r = _get_redis()
        if r is None:
            return {"success": False, "error": "Redis unavailable"}

        # 最新 20 件の失敗パターンからテーマを抽出
        raw_failures = r.lrange("atlas:failures", -20, -1)
        failures = []
        for raw in raw_failures:
            try:
                failures.append(json.loads(raw))
            except json.JSONDecodeError:
                pass

        if not failures:
            topic = "improve code generation quality"
        else:
            errors = [f.get("error", "")[:80] for f in failures if f.get("error")]
            stop_reasons = list({f.get("stop_reason", "") for f in failures})
            topic = (
                f"Fix common code generation failures: {', '.join(stop_reasons[:3])}. "
                f"Top errors: {'; '.join(errors[:3])}"
            )[:200]

        logger.info("AI-Scientist run_from_failures: topic=%s", topic[:80])
        ideas = self.run_ideas(topic, num_ideas=MAX_IDEAS, model=model)

        stored = 0
        for idea in ideas:
            _push_finding(r, topic, idea, {})
            hint = idea.get("fitness_hint") or idea.get("Interestingness") or ""
            if hint:
                _push_fitness_hint(r, str(hint)[:100])
                stored += 1

        return {
            "success": True,
            "topic": topic,
            "ideas_generated": len(ideas),
            "hints_stored": stored,
        }

    # ── internal: SakanaAI 実装 ──────────────────────────────────────────

    def _make_llm_kwargs(self, model: Optional[str]) -> dict:
        m = (model or f"ollama/{OLLAMA_MODEL}").removeprefix("ollama/")
        return {
            "model": f"ollama/{m}",
            "temperature": 0.7,
            "top_p": 0.95,
        }

    def _run_ideas_sakana(self, topic: str, template: str, num_ideas: int, model: Optional[str]) -> list[dict]:
        from ai_scientist.generate_ideas import generate_ideas  # type: ignore[import]

        llm_kwargs = self._make_llm_kwargs(model)
        ideas = generate_ideas(
            base_dir=str(Path(_AI_SCIENTIST_DIR) / "templates" / template),
            model=llm_kwargs["model"],
            skip_generation=False,
            max_num_generations=num_ideas,
            num_reflections=2,
        )
        return ideas if isinstance(ideas, list) else []

    def _run_experiment_sakana(self, idea: dict, template: str, model: Optional[str]) -> dict:
        from ai_scientist.perform_experiments import perform_experiments  # type: ignore[import]

        llm_kwargs = self._make_llm_kwargs(model)
        success, msg = perform_experiments(
            idea=idea,
            folder_name=str(Path(_AI_SCIENTIST_DIR) / "templates" / template),
            results_dir=str(Path(_AI_SCIENTIST_DIR) / "_results"),
            model=llm_kwargs["model"],
            run_num=1,
            timeout=300,
            max_runs=3,
        )
        return {"success": success, "message": msg}

    # ── fallback: LLM 直接呼び出し (SakanaAI が import できない場合) ──────

    def _fallback_ideas(self, topic: str, num_ideas: int, model: Optional[str]) -> list[dict]:
        """
        ai_scientist パッケージが利用不可の場合、Ollama に直接問い合わせてアイデアを生成する。
        """
        import requests

        m = (model or f"ollama/{OLLAMA_MODEL}").removeprefix("ollama/")
        system_prompt = (
            "You are an AI research scientist generating novel research ideas. "
            "Given a topic, output a JSON array of research ideas. "
            "Each idea must have: Name, Title, Experiment, Interestingness (1-10), "
            "Feasibility (1-10), Novelty (1-10), fitness_hint (actionable improvement directive, max 100 chars). "
            "Return ONLY valid JSON array."
        )
        user_msg = f"Generate {num_ideas} research ideas for: {topic}"

        try:
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/chat/completions",
                json={
                    "model": m,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
                timeout=120,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return self._parse_ideas_json(content)
        except Exception as e:
            logger.error("Fallback idea generation failed: %s", e)
            return []

    def _parse_ideas_json(self, content: str) -> list[dict]:
        import re
        for pattern in [r"```json\n?(.*?)```", r"```\n?(.*?)```", r"(\[.*?\])"]:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if isinstance(data, list):
                        return data
                except json.JSONDecodeError:
                    pass
        try:
            data = json.loads(content.strip())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
        return []


# ── デーモンエントリポイント ──────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    runner = AiScientistRunner()
    logger.info(
        "AI Scientist Runner starting (interval=%ds, model=ollama/%s, available=%s)",
        INTERVAL_SEC,
        OLLAMA_MODEL,
        runner._available,
    )
    while True:
        try:
            result = runner.run_from_failures()
            logger.info("Cycle done: %s", result)
        except Exception as e:
            logger.error("Cycle error: %s", e)
        logger.info("Next cycle in %d seconds", INTERVAL_SEC)
        time.sleep(INTERVAL_SEC)
