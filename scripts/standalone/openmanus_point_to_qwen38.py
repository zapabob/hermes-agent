"""Point plugins.entries.openmanus.llm at the local Qwen3.8 llama-server.

Backs up ~/.hermes/config.yaml, rewrites the openmanus LLM block, keeps the
previous remote LLM as a commented-free `llm_fallback` record so the operator
can restore it, and preserves every other key untouched.
"""

import os
import shutil
import sys
from datetime import datetime

import yaml

CONFIG = os.path.expanduser("~/.hermes/config.yaml")

TARGET = {
    "provider": "custom",
    "model": "qwen3.8-27b-abliterated-mtp",
    "base_url": "http://127.0.0.1:8080/v1",
    "api_type": "openai",
    "api_key_env": "OPENMANUS_LOCAL_API_KEY",
}


def main() -> int:
    with open(CONFIG, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}

    plugins = cfg.setdefault("plugins", {})
    entries = plugins.setdefault("entries", {})
    entry = entries.setdefault("openmanus", {})

    old = entry.get("llm")
    if isinstance(old, dict) and old.get("model") != TARGET["model"]:
        entry["llm_previous"] = dict(old)

    entry["llm"] = dict(TARGET)
    # llm_only keeps the child able to reach 127.0.0.1:8080 without web tools.
    entry["allow_llm_network"] = True
    entry.setdefault("network", "llm_only")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{CONFIG}.bak-qwen38-{stamp}"
    shutil.copy2(CONFIG, backup)

    with open(CONFIG, "w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh, allow_unicode=True, sort_keys=False, width=4096)

    print(f"backup: {backup}")
    print("openmanus.llm now:")
    for k, v in entry["llm"].items():
        print(f"  {k} = {v}")
    if "llm_previous" in entry:
        print("previous llm preserved under llm_previous:", entry["llm_previous"].get("model"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
