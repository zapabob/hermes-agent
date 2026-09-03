"""Antigravity (agy) harness core — isolated agy --print bridge.

Design:
- Zero runtime dependency on agy; missing binary surfaces as JSON error.
- Plugin-isolated: all agy invocation stays in this file, never in core.
- Native permission checks stay enabled and execution uses an empty workspace.
- Child environments and returned output are sanitized.

Binary resolution order:
  1. AGY_BIN env var (explicit override)
  2. shutil.which("agy") / which("agy.exe")
  3. Known Windows install paths
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from agent.redact import redact_sensitive_text
from tools.environments.local import hermes_subprocess_env


def _agy_candidates() -> list[str | None]:
    home = os.path.expanduser("~")
    return [
        os.environ.get("AGY_BIN"),
        shutil.which("agy"),
        shutil.which("agy.exe"),
        os.path.join(home, "AppData", "Local", "agy", "bin", "agy"),
        os.path.join(home, "AppData", "Local", "agy", "bin", "agy.exe"),
    ]


def _is_executable_candidate(candidate: str) -> bool:
    if not os.path.isfile(candidate):
        return False
    if os.name == "nt":
        return Path(candidate).suffix.lower() in {".exe", ".com"}
    return os.access(candidate, os.X_OK)


def find_agy_bin() -> str | None:
    for c in _agy_candidates():
        if c and _is_executable_candidate(c):
            return c
    return None


def _run_probe(args: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="hermes-antigravity-probe-") as workdir:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir,
            stdin=subprocess.DEVNULL,
            env=hermes_subprocess_env(allowlist_only=True),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )


def status_payload() -> dict[str, Any]:
    bin_path = find_agy_bin()
    if not bin_path:
        return {
            "available": False,
            "agy_bin": None,
            "auth": False,
            "models": [],
            "error": "agy binary not found. Install Antigravity CLI or set AGY_BIN.",
        }
    # probe version + models without leaking secrets
    version = None
    models: list[str] = []
    auth_ok = False
    try:
        r = _run_probe([bin_path, "--version"], timeout=10)
        if r.returncode == 0:
            version = (
                redact_sensitive_text(r.stdout.strip().splitlines()[0], force=True)
                if r.stdout
                else None
            )
    except Exception:
        pass
    try:
        r = _run_probe([bin_path, "models"], timeout=15)
        if r.returncode == 0:
            auth_ok = True
            # parse model ids from output
            for line in r.stdout.splitlines():
                line = line.strip()
                if line and not line.startswith("=") and not line.startswith("-"):
                    # heuristic: first token is model id
                    token = line.split()[0] if line.split() else ""
                    if "/" in token or "gemini" in token or "claude" in token or "gpt" in token:
                        models.append(redact_sensitive_text(token, force=True))
    except Exception:
        pass
    return {
        "available": bool(bin_path),
        "agy_bin": Path(bin_path).name,
        "version": version,
        "auth": auth_ok,
        "models": models[:20],
    }


def run_agy(
    prompt: str,
    *,
    model: str | None = None,
    timeout: int = 300,
) -> dict[str, Any]:
    bin_path = find_agy_bin()
    if not bin_path:
        return {"success": False, "error": "agy binary not found", "agy_bin": None}
    if not prompt or not prompt.strip():
        return {"success": False, "error": "prompt is required"}

    cmd: list[str] = [bin_path, "--print", prompt]
    if model:
        cmd.extend(["--model", model])

    timeout = max(1, min(int(timeout), 600))

    try:
        with tempfile.TemporaryDirectory(prefix="hermes-antigravity-") as workdir:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workdir,
                stdin=subprocess.DEVNULL,
                env=hermes_subprocess_env(allowlist_only=True),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        return {
            "success": r.returncode == 0,
            "exit_code": r.returncode,
            "stdout": redact_sensitive_text(r.stdout[:20000], force=True) if r.stdout else "",
            "stderr": redact_sensitive_text(r.stderr[:5000], force=True) if r.stderr else "",
            "agy_bin": Path(bin_path).name,
            "model": model,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"timeout after {timeout}s", "agy_bin": Path(bin_path).name}
    except Exception as exc:
        return {
            "success": False,
            "error": redact_sensitive_text(str(exc), force=True),
            "agy_bin": Path(bin_path).name,
        }
