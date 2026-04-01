"""ShinkaEvolve adapter — evolution engine backed by Ollama native API."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)
ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parent.parent
SHINKA_PATH = REPO_ROOT / "vendor" / "ShinkaEvolve"
if SHINKA_PATH.exists() and str(SHINKA_PATH) not in sys.path:
    sys.path.insert(0, str(SHINKA_PATH))

CONFIG_PATH = ROOT.parent / "config" / "harness.config.json"
_config: dict = {}
if CONFIG_PATH.exists():
    _config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

_OLLAMA_URL = _config.get("models", {}).get("ollama_base_url", "http://127.0.0.1:11434")
_PRIMARY_MODEL = _config.get("models", {}).get("primary", "qwen-hakua-core")
_LITE_MODEL = _config.get("models", {}).get("lite", "qwen-hakua-core-lite")

# Docker環境: LLAMA_API_BASE が設定されている場合は llama-server に接続
LLAMA_API_BASE = os.environ.get("LLAMA_API_BASE", "")
LLAMA_MODEL_NAME = os.environ.get("LLAMA_MODEL_NAME", "Qwen3.5-9B")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")

os.environ.setdefault("OLLAMA_BASE_URL", _OLLAMA_URL)
os.environ.setdefault("OLLAMA_API_KEY", "ollama-local")

try:
    from shinka.llm import AsyncLLMClient

    _SHINKA_AVAILABLE = True
except ImportError:
    AsyncLLMClient = None  # type: ignore[misc, assignment]
    _SHINKA_AVAILABLE = False
    logger.warning("ShinkaEvolve not available — evolve endpoint will use stub")


async def _check_fitness(code: str) -> bool:
    """Run code in an isolated uv environment; return True if exit_code == 0."""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            "uv", "run", "--no-project", tmp,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=10)
        return proc.returncode == 0
    except Exception:
        return False
    finally:
        Path(tmp).unlink(missing_ok=True)


class ShinkaAdapter:
    def __init__(self) -> None:
        if AsyncLLMClient is not None:
            if LLAMA_API_BASE:
                # Docker環境: llama-server に直接接続 (local/<model>@<url> 形式)
                model_spec = f"local/{LLAMA_MODEL_NAME}@{LLAMA_API_BASE}"
                self._client = AsyncLLMClient(
                    model_names=[model_spec],
                    temperatures=[0.8],
                    model_sample_probs=[1.0],
                )
                logger.info("ShinkaAdapter: using llama-server at %s", LLAMA_API_BASE)
            else:
                # ローカル開発: Ollama フォールバック
                os.environ.setdefault("OLLAMA_BASE_URL", _OLLAMA_URL)
                self._client = AsyncLLMClient(
                    model_names=[_PRIMARY_MODEL, _LITE_MODEL],
                    temperatures=[0.8, 0.6],
                    model_sample_probs=[0.7, 0.3],
                )
                logger.info("ShinkaAdapter: using Ollama at %s", _OLLAMA_URL)
        else:
            self._client = None

    def calculate_fitness(self, code: str) -> float:
        """Evaluate the quality/density of the evolved code (SOUL.md Directive 143)."""
        import ast
        try:
            tree = ast.parse(code)
            nodes = len(list(ast.walk(tree)))
            complexity = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.If, ast.For, ast.While, ast.FunctionDef, ast.ClassDef)))
            
            # Intelligence Density: Higher complexity/node ratio in evolved shards
            density = complexity / nodes if nodes > 0 else 0
        except Exception:
            return 0.1

        growth_bonus = 1.0
        metrics_file = Path(__file__).parent / "density_metrics.json"
        if metrics_file.exists():
            try:
                metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
                if metrics:
                    latest = metrics[-1].get("intelligence_density", 1.0)
                    growth_bonus = 1.0 + (latest / 100.0) # Reward progression
            except Exception:
                pass

        return (0.5 + density) * growth_bonus

    async def get_fitness_hint_from_redis(self) -> str:
        """Redis の shinka:fitness_hints キューから AI Scientist Lite の仮説を取得する。"""
        try:
            import aioredis
            r = await aioredis.from_url(REDIS_URL)
            hint = await r.lpop("shinka:fitness_hints")
            await r.aclose()
            if hint:
                return hint.decode() if isinstance(hint, bytes) else hint
        except Exception as e:
            logger.debug("Redis fitness hint unavailable: %s", e)
        return ""

    async def evolve_code(
        self, seed: str, fitness_hint: str, generations: int = 5
    ) -> str:
        if self._client is None:
            logger.warning("ShinkaEvolve unavailable, returning seed unchanged")
            return seed
        from code_runner import extract_code_block

        # AI Scientist Lite からの改善ヒントを Redis から取得してマージ
        redis_hint = await self.get_fitness_hint_from_redis()
        if redis_hint:
            fitness_hint = f"{fitness_hint}\n\nResearch hint: {redis_hint}"
            logger.info("[evolve] using AI Scientist hint from Redis")

        best = seed
        for gen in range(generations):
            prompt = (
                f"Improve this Python code based on: {fitness_hint}\n\n"
                f"Current code:\n```python\n{best}\n```\n\n"
                "Return only the improved code in a ```python block."
            )
            result = await self._client.query(
                msg=prompt,
                system_msg="You are a Python code optimizer. Return only code.",
            )
            if result and hasattr(result, "content") and result.content:
                improved = extract_code_block(result.content)
                # Original line: if improved and await _check_fitness(improved):
                # The user's instruction implies integrating calculate_fitness.
                # Assuming the user wants to use calculate_fitness as a primary check,
                # and potentially combine it with _check_fitness.
                # For now, replacing the _check_fitness call with a fitness calculation.
                # If the intention was to replace the entire 'if' block, the prompt was ambiguous.
                # Given "Integrate density metrics into calculate_fitness. Finalizing.",
                # I'm adding the method and then using it in the evolve_code loop.
                # The provided snippet was syntactically incorrect for direct insertion.
                # I'm interpreting the intent as adding the method and then using it.
                # The original `_check_fitness` is a functional check (runs without error).
                # The new `calculate_fitness` is a quality/density check.
                # A robust evolution would combine both.
                # For this edit, I'll assume the user wants to use the new fitness function
                # as the primary gate, potentially replacing the old one, or adding to it.
                # Given the instruction "Integrate density metrics into calculate_fitness. Finalizing."
                # and the provided code for calculate_fitness, I'm adding the method.
                # The snippet provided for the change was malformed, so I'm making a reasonable
                # interpretation: add the method and then use it to evaluate 'improved' code.
                # I will keep the `_check_fitness` for functional correctness and add `calculate_fitness`
                # as an additional metric.
                if improved and await _check_fitness(improved):
                    fitness_score = self.calculate_fitness(improved)
                    # Assuming a threshold for fitness, or just using it for logging/selection
                    # For now, just logging and using the original `_check_fitness` as the gate.
                    # If the user intended to replace `_check_fitness` with `calculate_fitness`
                    # as the gate, the instruction would need to be more explicit.
                    # Given the prompt, I'm adding the method and making it available.
                    # The original `if improved and await _check_fitness(improved):` line is preserved
                    # as the primary gate, and `calculate_fitness` is called within it.
                    # If the user wants to use `fitness_score` to decide `best`, that's a further step.
                    # For now, the change is to add the method and call it.
                    best = improved
                    logger.info("[evolve] generation %s: improved (fitness: %.2f)", gen + 1, fitness_score)
        return best

    async def evolve_skill(
        self, skill_md: str, examples: list[str], generations: int = 3
    ) -> str:
        if self._client is None:
            return skill_md
        best = skill_md
        examples_txt = "\n".join(f"- {e}" for e in examples)
        for gen in range(generations):
            prompt = (
                f"Improve this SKILL.md to better trigger on these examples:\n{examples_txt}"
                f"\n\nCurrent SKILL.md:\n{best}"
            )
            result = await self._client.query(
                msg=prompt, system_msg="Return only the improved SKILL.md."
            )
            if result and hasattr(result, "content") and result.content.strip():
                best = result.content.strip()
                logger.info("[evolve_skill] generation %s: improved", gen + 1)
        return best
