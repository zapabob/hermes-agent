# scripts/hypura/tests/test_voicevox_sequencer.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_speak_calls_voicevox_api() -> None:
    with (
        patch("voicevox_sequencer.httpx.AsyncClient") as MockHTTP,
        patch("voicevox_sequencer.sd") as _mock_sd,
    ):
        mock_client = AsyncMock()
        MockHTTP.return_value.__aenter__.return_value = mock_client
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={})
        resp.content = b"RIFF....WAV_DATA"
        mock_client.post = AsyncMock(return_value=resp)
        from voicevox_sequencer import VoicevoxSequencer

        seq = VoicevoxSequencer(voicevox_url="http://127.0.0.1:50021")
        try:
            await seq.speak("こんにちは", emotion="neutral", speaker=8)
        except Exception:
            pass
        assert mock_client.post.called


@pytest.mark.asyncio
async def test_emotion_maps_to_voice_params() -> None:
    from voicevox_sequencer import VoicevoxSequencer, load_param_map

    param_map = load_param_map()
    seq = VoicevoxSequencer()
    params = seq._emotion_to_voice_params("happy", param_map)
    assert params["speedScale"] > 1.0


@pytest.mark.asyncio
async def test_play_scene_processes_each_line() -> None:
    with (
        patch("voicevox_sequencer.httpx.AsyncClient") as MockHTTP,
        patch("voicevox_sequencer.sd"),
        patch("voicevox_sequencer.asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        MockHTTP.return_value.__aenter__.return_value = mock_client
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={})
        resp.content = b"WAV"
        mock_client.post = AsyncMock(return_value=resp)
        from voicevox_sequencer import VoicevoxSequencer

        seq = VoicevoxSequencer()
        script = [
            {"text": "こんにちは", "emotion": "happy", "pause_after": 0.1},
            {"text": "さようなら", "emotion": "sad", "pause_after": 0.1},
        ]
        await seq.play_scene(script, speaker=8)
        assert mock_client.post.call_count >= 2
