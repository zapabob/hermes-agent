"""Direct OpenManus + Qwen3.8 harness probe.

Bypasses the Hermes tool wrapper's 420s cap by invoking plugins/openmanus/runner.py
as a background-friendly child, then writing an explicit receipt of what actually
happened. Verifies the local llama-server LLM path end-to-end.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

VENV_PY = REPO_ROOT / "_runtime" / "openmanus-venv" / "Scripts" / "python.exe"
RUNNER = REPO_ROOT / "plugins" / "openmanus" / "runner.py"
SOURCE_ROOT = REPO_ROOT / "vendor" / "openmanus"
WORKSPACE_ROOT = REPO_ROOT / "_runtime" / "research-workspace"

BASE_URL = "http://127.0.0.1:8080/v1"
MODEL = "qwen3.8-27b-abliterated-mtp"
API_KEY_ENV = "OPENMANUS_API_KEY"

PROMPT = (
    "Create a file named harness_ok.txt in the current working directory. "
    "It must contain exactly the single line HARNESS_OK. "
    "After the file exists, call terminate."
)


def main() -> int:
    max_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 1800

    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-direct"
    run_root = Path(os.path.expanduser("~/.hermes")) / "openmanus" / "runs" / run_id
    run_root.mkdir(parents=True, exist_ok=True)

    # Load the secret from ~/.hermes/.env so a bare `py -3` invocation works.
    from hermes_cli.config import reload_env

    reload_env()
    secret = os.environ.get(API_KEY_ENV, "")
    if not secret:
        print(f"FATAL: {API_KEY_ENV} not set after reload_env()", file=sys.stderr)
        return 2

    cmd = [
        str(VENV_PY),
        str(RUNNER),
        "--source-root", str(SOURCE_ROOT),
        "--workspace-root", str(WORKSPACE_ROOT),
        "--run-root", str(run_root),
        "--model", MODEL,
        "--base-url", BASE_URL,
        "--api-type", "openai",
        "--api-key-env", API_KEY_ENV,
        "--agent-mode", "manus",
        "--max-steps", str(max_steps),
        "--allow-network",
        "--network-scope", "llm_only",
    ]

    env = dict(os.environ)
    env[API_KEY_ENV] = secret
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    print(f"run_id: {run_id}")
    print(f"run_root: {run_root}")
    print(f"model: {MODEL} @ {BASE_URL}")
    print(f"max_steps: {max_steps} timeout: {timeout}s")
    started = time.time()

    proc = subprocess.run(
        cmd,
        input=PROMPT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=timeout,
    )

    elapsed = round(time.time() - started, 1)

    result_text = ""
    for line in (proc.stdout or "").splitlines():
        if line.startswith("__HERMES_OPENMANUS_RESULT__:"):
            try:
                result_text = json.loads(line.split(":", 1)[1]).get("result", "")
            except Exception:
                result_text = line

    receipt = {
        "run_id": run_id,
        "elapsed_seconds": elapsed,
        "exit_code": proc.returncode,
        "model": MODEL,
        "base_url": BASE_URL,
        "network_scope": "llm_only",
        "max_steps": max_steps,
        "result": result_text,
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-8000:],
    }
    receipt_path = run_root / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nexit_code: {proc.returncode}  elapsed: {elapsed}s")
    print(f"receipt: {receipt_path}")
    print(f"\nRESULT:\n{result_text[:2000]}")
    print(f"\nSTDERR TAIL:\n{(proc.stderr or '')[-3000:]}")
    return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
