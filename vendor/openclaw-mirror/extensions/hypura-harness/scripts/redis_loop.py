"""
Redis ループヘルパー — Openclaw ハーネス ↔ Hypura ハーネスの継続改善ループ。

Redis キー設計:
  training:examples  (LIST)  → TinyLoRA 学習用成功サンプル
  atlas:failures     (LIST)  → AI Scientist Lite 分析用失敗パターン
  shinka:fitness_hints (LIST) → ShinkaEvolve が参照する改善ヒント
  lora:training_lock  (STRING) → 学習中フラグ (lora_watcher が管理)
  lora:tinylora_adapter (STRING) → 最新アダプター JSON

ループ全体図:
  /run ──────── 成功 ──────────────────────────────→ training:examples
    │                                                        │
    └──── 失敗(max_retries) ──→ atlas:failures              │
              │                      │                       ↓
              │               ai_scientist_lite        lora_watcher
              │                      │                (TinyLoRA GRPO)
              │               shinka:fitness_hints          │
              │                      │                       │
              └──── /evolve ◄────────┘           adapter updated
                       │
                  成功 → training:examples (quality_score 低め)
                  失敗 → atlas:failures
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Redis 接続 (オプション — 未接続でも動作する)
_redis = None
_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


def _get_redis():
    """Redis クライアントを遅延初期化する。失敗しても None を返すだけ。"""
    global _redis
    if _redis is not None:
        return _redis
    try:
        import redis as redis_lib
        url = _REDIS_URL.removeprefix("redis://")
        host, _, port = url.partition(":")
        _redis = redis_lib.Redis(host=host or "localhost", port=int(port or 6379), decode_responses=True)
        _redis.ping()
        logger.info("Redis connected: %s", _REDIS_URL)
    except Exception as e:
        logger.debug("Redis unavailable (loop disabled): %s", e)
        _redis = None
    return _redis


def push_training_example(
    *,
    task: str,
    code: str,
    output: str = "",
    quality_score: float = 1.0,
    source: str = "run",
    meta: Optional[dict] = None,
) -> bool:
    """
    成功したコード生成を training:examples に保存する。
    lora_watcher が LORA_TRAINING_THRESHOLD 件蓄積後に TinyLoRA 学習を起動する。

    quality_score:
      1.0  = 一発成功
      0.8  = 1回リトライ後成功
      0.6  = 2回リトライ後成功
      0.5  = evolve 後成功
    """
    r = _get_redis()
    if r is None:
        return False
    try:
        record = {
            "prompt": task[:1000],
            "completion": code[:4000],
            "output": output[:500],
            "quality_score": quality_score,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(meta or {}),
        }
        r.rpush("training:examples", json.dumps(record))
        count = r.llen("training:examples")
        logger.info("training:examples: %d (quality=%.1f, src=%s)", count, quality_score, source)
        return True
    except Exception as e:
        logger.warning("push_training_example failed: %s", e)
        return False


def push_failure(
    *,
    task: str,
    stop_reason: str,
    error: str = "",
    attempts: int = 0,
    source: str = "run",
) -> bool:
    """
    失敗パターンを atlas:failures に保存する。
    ai_scientist_lite が読み込んで shinka:fitness_hints を生成する。
    """
    r = _get_redis()
    if r is None:
        return False
    try:
        record = {
            "prompt": task[:500],
            "stop_reason": stop_reason,
            "error": error[:500],
            "attempts": attempts,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        r.rpush("atlas:failures", json.dumps(record))
        r.ltrim("atlas:failures", -500, -1)  # 最新 500 件
        logger.info("atlas:failures: stop_reason=%s, src=%s", stop_reason, source)
        return True
    except Exception as e:
        logger.warning("push_failure failed: %s", e)
        return False


def get_fitness_hints(max_hints: int = 3) -> list[str]:
    """
    shinka:fitness_hints から最大 max_hints 件のヒントを取得する。
    ShinkaEvolve が進化プロンプトに付加する改善方向として使用する。
    """
    r = _get_redis()
    if r is None:
        return []
    try:
        hints = []
        for _ in range(max_hints):
            h = r.lpop("shinka:fitness_hints")
            if h is None:
                break
            hints.append(h)
        if hints:
            logger.debug("fitness_hints consumed: %d", len(hints))
        return hints
    except Exception as e:
        logger.warning("get_fitness_hints failed: %s", e)
        return []


def is_training_in_progress() -> bool:
    """TinyLoRA 学習中かどうかを確認する (llama-service 停止中の推論回避)。"""
    r = _get_redis()
    if r is None:
        return False
    try:
        return bool(r.exists("lora:training_lock"))
    except Exception:
        return False


def get_loop_stats() -> dict:
    """ループの現在状態を返す (/status エンドポイント用)。"""
    r = _get_redis()
    if r is None:
        return {"redis": "unavailable"}
    try:
        return {
            "redis": "connected",
            "training_examples": r.llen("training:examples"),
            "failures": r.llen("atlas:failures"),
            "fitness_hints": r.llen("shinka:fitness_hints"),
            "training_in_progress": bool(r.exists("lora:training_lock")),
            "last_trained": r.get("lora:last_trained"),
            "tinylora_adapter_ready": bool(r.exists("lora:tinylora_adapter")),
            "scientist_findings": r.llen("ai_scientist:findings"),
            "scientist_tasks": r.llen("ai_scientist:tasks"),
        }
    except Exception as e:
        return {"redis": "error", "error": str(e)}


# ── AI Scientist ループヘルパー ───────────────────────────────────────────

def push_scientist_finding(
    *,
    topic: str,
    idea: dict,
    result: dict,
) -> bool:
    """
    AI-Scientist の発見を ai_scientist:findings に保存する (max 200 件)。
    有用な fitness_hint があれば shinka:fitness_hints にも追加する。
    """
    r = _get_redis()
    if r is None:
        return False
    try:
        record = {
            "topic": topic[:300],
            "idea": idea,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        r.rpush("ai_scientist:findings", json.dumps(record, ensure_ascii=False))
        r.ltrim("ai_scientist:findings", -200, -1)

        hint = (idea.get("fitness_hint") or idea.get("Interestingness") or "")
        if hint:
            r.rpush("shinka:fitness_hints", str(hint)[:100])
            r.ltrim("shinka:fitness_hints", -100, -1)

        logger.info(
            "ai_scientist:findings: +1 (topic=%s, hints_added=%s)",
            topic[:40],
            bool(hint),
        )
        return True
    except Exception as e:
        logger.warning("push_scientist_finding failed: %s", e)
        return False


def get_scientist_tasks(max_tasks: int = 3) -> list[dict]:
    """
    ai_scientist:tasks キューから最大 max_tasks 件のタスクを取り出す。
    外部 (openclaw agent 等) からタスクを投入できる。

    タスク形式: {"topic": "...", "num_ideas": 3, "model": "ollama/..."}
    """
    r = _get_redis()
    if r is None:
        return []
    tasks = []
    try:
        for _ in range(max_tasks):
            raw = r.lpop("ai_scientist:tasks")
            if raw is None:
                break
            try:
                tasks.append(json.loads(raw))
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.warning("get_scientist_tasks failed: %s", e)
    return tasks
