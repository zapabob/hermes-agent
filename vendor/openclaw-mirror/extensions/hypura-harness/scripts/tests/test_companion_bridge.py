# scripts/hypura/tests/test_companion_bridge.py
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from companion_bridge import CompanionBridge


@pytest.mark.asyncio
async def test_forward_speak_posts_to_companion() -> None:
    with patch("companion_bridge.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = mock_client
        mock_cls.return_value.__aexit__.return_value = None

        bridge = CompanionBridge("http://127.0.0.1:18791")
        await bridge.forward_speak("hello", "happy")

        mock_client.post.assert_awaited_once()
        call_args = mock_client.post.await_args
        assert call_args[0][0] == "http://127.0.0.1:18791/control"
        assert call_args[1]["json"]["speakText"] == "hello"
        assert call_args[1]["json"]["avatarCommand"] == {
            "type": "emotion",
            "emotion": "happy",
        }


@pytest.mark.asyncio
async def test_forward_emotion_posts_correct_payload() -> None:
    with patch("companion_bridge.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = mock_client
        mock_cls.return_value.__aexit__.return_value = None

        bridge = CompanionBridge("http://127.0.0.1:18791")
        await bridge.forward_emotion("neutral")

        mock_client.post.assert_awaited_once()
        call_args = mock_client.post.await_args
        assert call_args[0][0] == "http://127.0.0.1:18791/control"
        assert call_args[1]["json"] == {
            "avatarCommand": {"type": "emotion", "emotion": "neutral"},
        }


@pytest.mark.asyncio
async def test_forward_speak_silently_fails_when_companion_down() -> None:
    with patch("companion_bridge.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        req = MagicMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("connection refused", request=req)
        )
        mock_cls.return_value.__aenter__.return_value = mock_client
        mock_cls.return_value.__aexit__.return_value = None

        bridge = CompanionBridge("http://127.0.0.1:18791")
        await bridge.forward_speak("hi", "neutral")
