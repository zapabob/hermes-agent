"""VOICEVOX TTS sequencer — outputs to VB-Cable virtual microphone."""
from __future__ import annotations

import asyncio
import io
import json
import logging
from pathlib import Path
from typing import Any

import httpx
import sounddevice as sd
import soundfile as sf

logger = logging.getLogger(__name__)
ROOT = Path(__file__).parent


def load_param_map() -> dict:
    p = ROOT / "osc_param_map.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _find_cable_device(name: str = "CABLE Input") -> int | None:
    try:
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if name.lower() in d["name"].lower() and d["max_output_channels"] > 0:
                return i
    except Exception:
        pass
    return None


class VoicevoxSequencer:
    def __init__(
        self,
        voicevox_url: str = "http://127.0.0.1:50021",
        cable_device_name: str = "CABLE Input",
    ) -> None:
        self._url = voicevox_url
        self._device = _find_cable_device(cable_device_name)
        if self._device is None:
            logger.warning("VB-Cable not found, using default output device")

    def _emotion_to_voice_params(self, emotion: str, param_map: dict) -> dict:
        vx_emotions = param_map.get("voicevox_emotions", {})
        return vx_emotions.get(emotion) or vx_emotions.get("neutral") or {
            "speedScale": 1.0,
            "pitchScale": 0.0,
            "intonationScale": 1.0,
        }

    async def speak(self, text: str, emotion: str = "neutral", speaker: int = 8) -> None:
        """Synthesize text and play through VB-Cable."""
        param_map = load_param_map()
        voice_params = self._emotion_to_voice_params(emotion, param_map)
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{self._url}/audio_query",
                params={"text": text, "speaker": speaker},
            )
            r.raise_for_status()
            query = r.json()
            query.update(voice_params)
            r2 = await client.post(
                f"{self._url}/synthesis",
                params={"speaker": speaker},
                json=query,
            )
            r2.raise_for_status()
            wav_bytes = r2.content
        try:
            data, samplerate = sf.read(io.BytesIO(wav_bytes))
            sd.play(data, samplerate, device=self._device)
            sd.wait()
        except Exception as e:
            logger.warning("Audio playback failed: %s", e)

    async def play_scene(self, script: list[dict[str, Any]], speaker: int = 8) -> None:
        """Play a sequence of lines with pauses."""
        for line in script:
            text = line.get("text", "")
            emotion = line.get("emotion", "neutral")
            pause = line.get("pause_after", 0.5)
            if text:
                try:
                    await self.speak(text, emotion=emotion, speaker=speaker)
                except Exception as e:
                    logger.warning("speak failed for '%s': %s", text[:20], e)
            await asyncio.sleep(pause)
