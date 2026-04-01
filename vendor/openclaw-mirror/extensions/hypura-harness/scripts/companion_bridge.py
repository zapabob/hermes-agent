"""Forward Hypura daemon actions to the Live2D Companion HTTP control endpoint."""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class CompanionBridge:
    """POSTs to ``{companion_url}/control`` for speak + avatar emotion sync."""

    def __init__(self, companion_url: str) -> None:
        self._base = companion_url.rstrip("/")

    async def forward_speak(self, text: str, emotion: str) -> None:
        url = f"{self._base}/control"
        payload: dict[str, Any] = {
            "speakText": text,
            "avatarCommand": {"type": "emotion", "emotion": emotion},
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(url, json=payload)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            logger.warning("Companion bridge forward_speak failed: %s", e)

    async def forward_emotion(self, emotion: str) -> None:
        url = f"{self._base}/control"
        payload: dict[str, Any] = {
            "avatarCommand": {"type": "emotion", "emotion": emotion},
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(url, json=payload)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            logger.warning("Companion bridge forward_emotion failed: %s", e)
