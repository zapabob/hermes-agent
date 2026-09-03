"""hermes-antigravity — Antigravity CLI (agy) isolated harness plugin.

Zero runtime dependency on Nous; agy is called only via isolated subprocess
in plugins/hermes-antigravity/core.py. No core files are touched.
"""

from __future__ import annotations

import json
from typing import Any

from .core import find_agy_bin, run_agy, status_payload


def _status_handler(_: Any = None, **__: Any) -> str:
    return json.dumps(status_payload(), ensure_ascii=False, indent=2)


def _run_handler(args: Any = None, **__: Any) -> str:
    data = args if isinstance(args, dict) else {}
    result = run_agy(
        prompt=str(data.get("prompt") or ""),
        model=data.get("model"),
        timeout=int(data.get("timeout") or 300),
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


def _models_handler(_: Any = None, **__: Any) -> str:
    payload = status_payload()
    return json.dumps(
        {"available": payload.get("available"), "auth": payload.get("auth"), "models": payload.get("models"), "agy_bin": payload.get("agy_bin")},
        ensure_ascii=False,
        indent=2,
    )


def register(ctx) -> None:
    ctx.register_tool(
        name="antigravity_status",
        toolset="antigravity",
        schema={"type": "object", "properties": {}},
        handler=_status_handler,
        check_fn=lambda: True,
        description="Report Antigravity CLI (agy) binary presence, version, auth and available models without leaking secrets.",
    )

    ctx.register_tool(
        name="antigravity_models",
        toolset="antigravity",
        schema={"type": "object", "properties": {}},
        handler=_models_handler,
        check_fn=lambda: find_agy_bin() is not None,
        description="List available Antigravity models (gemini-3.8, claude-sonnet-4-6, etc.) when authenticated.",
    )

    ctx.register_tool(
        name="antigravity_run",
        toolset="antigravity",
        schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "prompt": {"type": "string", "description": "Prompt to send to agy --print"},
                "model": {"type": "string", "description": "Optional model id, e.g. gemini-3.8-flash-high, claude-sonnet-4-6"},
                "timeout": {"type": "integer", "minimum": 1, "maximum": 600, "description": "Timeout seconds (default 300, maximum 600)"},
            },
            "required": ["prompt"],
        },
        handler=_run_handler,
        check_fn=lambda: find_agy_bin() is not None,
        description="Run Antigravity CLI headless in an empty temporary workspace with its native permission checks enabled.",
    )
