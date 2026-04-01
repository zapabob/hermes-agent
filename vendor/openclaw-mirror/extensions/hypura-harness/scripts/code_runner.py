"""Code runner — uses OpenClaw CLI (or Codex CLI) to generate code, then runs with uv."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "harness.config.json"
GENERATED_DIR = ROOT / "generated"
EVOLVED_DIR = ROOT / "evolved"
GENERATED_DIR.mkdir(exist_ok=True)
EVOLVED_DIR.mkdir(exist_ok=True)

_config: dict = {}
if CONFIG_PATH.exists():
    _config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

_MAX_GENERATED = _config.get("generated_max_files", 50)
_EXEC_TIMEOUT = _config.get("execution_timeout_sec", 60)
_OPENCLAW_CFG = _config.get("openclaw", {}) if isinstance(_config.get("openclaw"), dict) else {}
_OPENCLAW_CLI = (
    _OPENCLAW_CFG.get("cli_binary", "openclaw")
    if isinstance(_OPENCLAW_CFG.get("cli_binary"), str)
    else "openclaw"
)
_USE_GATEWAY_AGENT = bool(_OPENCLAW_CFG.get("use_gateway_agent", False))
_AGENT_EXTRA: list[str] = []
_raw_extra = _OPENCLAW_CFG.get("agent_extra_args")
if isinstance(_raw_extra, list):
    _AGENT_EXTRA = [str(x) for x in _raw_extra if isinstance(x, str)]


def extract_code_block(text: str) -> str:
    """Extract Python code from a markdown fenced block."""
    m = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def _prune_generated() -> None:
    """Keep only the most recent _MAX_GENERATED scripts."""
    files = sorted(GENERATED_DIR.glob("run_*.py"), key=lambda f: f.stat().st_mtime)
    if len(files) <= _MAX_GENERATED:
        return
    n_drop = len(files) - _MAX_GENERATED
    for old in files[:n_drop]:
        old.unlink(missing_ok=True)


def _generate_code(task: str, error_context: str = "") -> str:
    """Call OpenClaw CLI (optional gateway ``agent``) → ``run`` → Claude/Codex fallbacks."""
    prompt = (
        f"Write a self-contained Python script (PEP 723 inline deps) to: {task}"
        + (f"\n\nPrevious error:\n{error_context}" if error_context else "")
        + "\n\nStart with:\n# /// script\n# dependencies = [...]\n# ///"
    )
    attempts: list[tuple[str, list[str]]] = []
    if _USE_GATEWAY_AGENT:
        attempts.append(
            (
                f"{_OPENCLAW_CLI} agent",
                [_OPENCLAW_CLI, "agent", *_AGENT_EXTRA, "-m", prompt],
            )
        )
    attempts.append((f"{_OPENCLAW_CLI} run", [_OPENCLAW_CLI, "run", "--", prompt]))
    attempts.append(("claude", ["claude", "-p", prompt, "--output-format", "text"]))
    attempts.append(("codex", ["codex", "--quiet", prompt]))

    for _label, cmd in attempts:
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
            )
            if r.returncode == 0 and r.stdout.strip():
                return extract_code_block(r.stdout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    raise RuntimeError("All code generation backends failed")


class CodeRunner:
    def __init__(self, max_retries: int | None = None) -> None:
        if max_retries is not None:
            self._max_retries = max_retries
        else:
            self._max_retries = _config.get("evolution", {}).get(
                "max_retries_before_evolve", 3
            )

    def run_task(self, task: str, model: str = "auto") -> dict:
        """Generate + execute Python. Retry on failure. Returns result dict."""
        error_context = ""
        for _attempt in range(self._max_retries):
            try:
                code = _generate_code(task, error_context)
            except RuntimeError as e:
                return {"success": False, "error": str(e), "output": ""}

            if "# /// script" not in code:
                code = "# /// script\n# dependencies = []\n# ///\n" + code

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            h = hashlib.sha256(code.encode()).hexdigest()[:8]
            script_path = GENERATED_DIR / f"run_{ts}_{h}.py"
            script_path.write_text(code, encoding="utf-8")
            _prune_generated()

            try:
                r = subprocess.run(
                    ["uv", "run", "--script", str(script_path)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=_EXEC_TIMEOUT,
                    cwd=str(GENERATED_DIR),
                )
                if r.returncode == 0:
                    return {
                        "success": True,
                        "output": r.stdout,
                        "script": str(script_path),
                    }
                error_context = r.stderr or r.stdout
                logger.warning(
                    "Attempt failed: %s", (error_context or "")[:200]
                )
            except subprocess.TimeoutExpired:
                error_context = f"Execution timed out after {_EXEC_TIMEOUT}s"

        return {
            "success": False,
            "error": f"Failed after {self._max_retries} attempts",
            "output": "",
            "last_error": error_context,
        }
