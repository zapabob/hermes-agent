"""Compression regressions for official identical-result reference stubs."""

from unittest.mock import patch

import pytest

from agent.context_compressor import ContextCompressor
from agent.tool_guardrails import ToolCallGuardrailController
from tools.tool_result_storage import _build_persisted_message


def _tool_call(call_id: str) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": "web_search",
                    "arguments": '{"query":"same"}',
                },
            }
        ],
    }


def _tool_result(call_id: str, content: str) -> dict:
    return {
        "role": "tool",
        "name": "web_search",
        "tool_call_id": call_id,
        "content": content,
    }


def _generated_stub_sequence(payload: str, *, persisted_path: str | None) -> list[dict]:
    guardrails = ToolCallGuardrailController()
    args = {"query": "same"}
    first_id = "call_original"
    first = guardrails.observe_call(
        "web_search", args, payload, tool_call_id=first_id
    )
    assert first.stub is None
    if persisted_path:
        guardrails.record_persisted_result(first_id, persisted_path)
        original_in_context = _build_persisted_message(
            payload[:600],
            True,
            len(payload),
            persisted_path,
        )
    else:
        original_in_context = payload

    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "run the repeated lookup"},
        _tool_call(first_id),
        _tool_result(first_id, original_in_context),
    ]
    for index in range(2):
        call_id = f"call_stub_{index + 1}"
        observation = guardrails.observe_call(
            "web_search", args, payload, tool_call_id=call_id
        )
        assert observation.stub is not None
        content = observation.stub
        if observation.notice:
            content += "\n\n" + observation.notice
        messages.extend([_tool_call(call_id), _tool_result(call_id, content)])
    return messages


@pytest.mark.parametrize("persisted", [False, True])
def test_actual_compression_keeps_unique_payload_reachable_from_stubbed_tail(
    persisted: bool,
):
    unique = "UNIQUE-COMPRESSION-PAYLOAD-7f93"
    payload = unique + "\n" + ("result-data\n" * 280)  # about 3 KiB
    persisted_path = "/tmp/hermes/spill/call_original.txt" if persisted else None
    messages = _generated_stub_sequence(payload, persisted_path=persisted_path)

    # Keep only the newest call/result pair in the protected tail. Before the
    # seam fix, both rows were reference stubs while the original full payload
    # entered the summarized middle and disappeared verbatim.
    with patch(
        "agent.context_compressor.get_model_context_length", return_value=100_000
    ):
        compressor = ContextCompressor(
            model="test",
            quiet_mode=True,
            protect_first_n=1,
            protect_last_n=2,
        )
    compressor.tail_token_budget = 1
    with patch.object(compressor, "_generate_summary", return_value="summary"):
        compressed = compressor.compress(messages, current_tokens=99_999, force=True)

    tool_contents = [
        message.get("content", "")
        for message in compressed
        if message.get("role") == "tool"
    ]
    if persisted_path:
        assert any(persisted_path in content for content in tool_contents)
        assert any(unique in content for content in tool_contents)
    else:
        assert payload in tool_contents
    assert not all("byte-identical" in content for content in tool_contents)
