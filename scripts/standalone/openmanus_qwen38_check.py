"""Verify the Hermes openmanus plugin resolves the local Qwen3.8 llama-server.

Checks config wiring, secret availability, and that the resolved base_url
actually answers — without launching a full agent run.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

EXPECTED_MODEL = "qwen3.8-27b-abliterated-mtp"


def main() -> int:
    from hermes_cli.config import reload_env

    sys.path.insert(0, str(REPO_ROOT / "plugins"))
    from openmanus import core  # type: ignore

    reload_env()

    entry = core._load_entry()
    llm = core._llm_entry(entry)
    key_env = core._api_key_env(entry)

    problems: list[str] = []

    model = str(llm.get("model") or "")
    base_url = str(llm.get("base_url") or "")
    print(f"model        = {model}")
    print(f"base_url     = {base_url}")
    print(f"api_type     = {llm.get('api_type')}")
    print(f"api_key_env  = {key_env}")
    print(f"secret set   = {bool(os.environ.get(key_env))}")
    print(f"allow_llm_network = {entry.get('allow_llm_network')}")
    print(f"workspace_root    = {entry.get('workspace_root')}")

    if model != EXPECTED_MODEL:
        problems.append(f"model is {model!r}, expected {EXPECTED_MODEL!r}")
    if "127.0.0.1" not in base_url and "localhost" not in base_url:
        problems.append(f"base_url {base_url!r} is not the local llama-server")
    if not entry.get("allow_llm_network"):
        problems.append("allow_llm_network is false — network_scope=llm_only will be refused")
    if not os.environ.get(key_env):
        problems.append(f"secret env {key_env} is empty — live runs will be blocked")

    # Live endpoint probe.
    try:
        req = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(
                {
                    "model": model,
                    "messages": [{"role": "user", "content": "Reply with exactly: READY"}],
                    "max_tokens": 256,
                    "temperature": 0,
                }
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.environ.get(key_env, 'x')}",
            },
        )
        with urllib.request.urlopen(req, timeout=300) as fh:
            payload = json.load(fh)
        content = payload["choices"][0]["message"].get("content") or ""
        print(f"live probe   = {content.strip()!r} (served model: {payload.get('model')})")
        if not content.strip():
            problems.append("endpoint answered but content was empty")
    except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
        problems.append(f"live probe failed: {exc}")

    if problems:
        print("\nFAIL:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("\nOK: openmanus is wired to the local Qwen3.8 llama-server")
    return 0


if __name__ == "__main__":
    sys.exit(main())
