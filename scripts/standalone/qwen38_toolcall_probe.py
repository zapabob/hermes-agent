"""Minimal tool-calling probe against the local Qwen3.8 llama-server.

OpenManus drives the model with OpenAI tool-calling. If the served model does
not emit a well-formed tool_call, OpenManus retries forever and the run never
finishes even though the endpoint is healthy. This isolates that one behaviour.
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

BASE_URL = "http://127.0.0.1:8080/v1"
MODEL = "qwen3.8-27b-abliterated-mtp"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Write text content to a file on disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write."},
                    "content": {"type": "string", "description": "Exact file content."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "terminate",
            "description": "End the run once the task is complete.",
            "parameters": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": ["status"],
            },
        },
    },
]


def call(messages, tool_choice="auto", max_tokens=1024):
    body = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": tool_choice,
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    req = urllib.request.Request(
        BASE_URL + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('OPENMANUS_API_KEY', 'x')}",
        },
    )
    started = time.time()
    with urllib.request.urlopen(req, timeout=600) as fh:
        payload = json.load(fh)
    return payload, round(time.time() - started, 1)


def main() -> int:
    from hermes_cli.config import reload_env

    reload_env()

    messages = [
        {
            "role": "system",
            "content": "You are an agent. Use the provided tools to complete the task. Emit a tool call, not prose.",
        },
        {
            "role": "user",
            "content": "Create a file at harness_ok.txt containing exactly HARNESS_OK, then terminate.",
        },
    ]

    print(f"model: {MODEL}  tool_choice: auto")
    payload, elapsed = call(messages)
    choice = payload["choices"][0]
    msg = choice["message"]
    tool_calls = msg.get("tool_calls") or []

    print(f"elapsed        = {elapsed}s")
    print(f"finish_reason  = {choice.get('finish_reason')}")
    print(f"content        = {(msg.get('content') or '')[:200]!r}")
    print(f"reasoning len  = {len(msg.get('reasoning_content') or '')}")
    print(f"tool_calls     = {len(tool_calls)}")
    for tc in tool_calls:
        fn = tc.get("function", {})
        print(f"  -> {fn.get('name')} args={str(fn.get('arguments'))[:200]}")
    print(f"usage          = {payload.get('usage')}")

    if not tool_calls:
        print("\nFAIL: model produced no tool_call — OpenManus will retry forever")
        return 1
    print("\nOK: model emits OpenAI-shaped tool calls")
    return 0


if __name__ == "__main__":
    sys.exit(main())
