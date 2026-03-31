"""LINE platform adapter.

Receives LINE webhook events via aiohttp and sends replies/push messages
through the LINE Messaging API.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional

import httpx

try:
    from aiohttp import web

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    web = None  # type: ignore[assignment]

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import BasePlatformAdapter, MessageEvent, MessageType, SendResult

logger = logging.getLogger(__name__)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8650
LINE_API_BASE = "https://api.line.me/v2/bot/message"


def check_line_requirements() -> bool:
    return AIOHTTP_AVAILABLE


class LineAdapter(BasePlatformAdapter):
    """LINE Messaging API adapter."""

    MAX_MESSAGE_LENGTH = 5000

    def __init__(self, config: PlatformConfig):
        super().__init__(config, Platform.LINE)
        self._host = str(config.extra.get("host", DEFAULT_HOST))
        self._port = int(config.extra.get("port", DEFAULT_PORT))
        self._channel_secret = str(config.extra.get("channel_secret", ""))
        self._channel_access_token = config.token or ""
        self._runner = None
        # Keep latest replyToken for short-lived direct replies per chat.
        self._reply_tokens: Dict[str, tuple[str, float]] = {}

    async def connect(self) -> bool:
        if not self._channel_secret or not self._channel_access_token:
            logger.warning("LINE: missing LINE_CHANNEL_SECRET or LINE_CHANNEL_ACCESS_TOKEN")
            return False
        app = web.Application()
        app.router.add_get("/line/health", self._handle_health)
        app.router.add_post("/line/webhook", self._handle_webhook)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()
        self._mark_connected()
        logger.info("[line] Listening on %s:%d (/line/webhook)", self._host, self._port)
        return True

    async def disconnect(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._mark_disconnected()
        logger.info("[line] Disconnected")

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        chunks = self.truncate_message(content, self.MAX_MESSAGE_LENGTH)
        for chunk in chunks:
            result = await self._send_one(chat_id=chat_id, content=chunk)
            if not result.success:
                return result
        return SendResult(success=True)

    async def _send_one(self, chat_id: str, content: str) -> SendResult:
        headers = {
            "Authorization": f"Bearer {self._channel_access_token}",
            "Content-Type": "application/json",
        }
        now = time.time()
        reply_payload = self._reply_tokens.get(chat_id)
        # LINE replyToken is short-lived, best-effort under 50 sec.
        if reply_payload and now - reply_payload[1] < 50:
            url = f"{LINE_API_BASE}/reply"
            body = {"replyToken": reply_payload[0], "messages": [{"type": "text", "text": content}]}
        else:
            url = f"{LINE_API_BASE}/push"
            body = {"to": chat_id, "messages": [{"type": "text", "text": content}]}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, headers=headers, json=body)
            if res.status_code >= 400:
                return SendResult(success=False, error=f"LINE API {res.status_code}: {res.text}")
            return SendResult(success=True)
        except Exception as exc:
            return SendResult(success=False, error=f"LINE send failed: {exc}", retryable=True)

    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        return {"name": chat_id, "type": "dm"}

    async def _handle_health(self, request: "web.Request") -> "web.Response":
        return web.json_response({"status": "ok", "platform": "line"})

    def _verify_signature(self, body: bytes, signature: str) -> bool:
        mac = hmac.new(self._channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
        expected = base64.b64encode(mac).decode("utf-8")
        return hmac.compare_digest(expected, signature or "")

    async def _handle_webhook(self, request: "web.Request") -> "web.Response":
        body = await request.read()
        signature = request.headers.get("x-line-signature", "")
        if not self._verify_signature(body, signature):
            return web.json_response({"error": "invalid signature"}, status=401)

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return web.json_response({"error": "invalid json"}, status=400)

        events = payload.get("events", [])
        for event in events:
            await self._process_event(event)
        return web.json_response({"ok": True})

    async def _process_event(self, event: Dict[str, Any]) -> None:
        event_type = event.get("type")
        source = event.get("source", {}) or {}
        chat_id = source.get("userId") or source.get("groupId") or source.get("roomId")
        if not chat_id:
            return
        user_id = source.get("userId") or chat_id
        reply_token = event.get("replyToken")
        if isinstance(reply_token, str) and reply_token:
            self._reply_tokens[str(chat_id)] = (reply_token, time.time())

        if event_type == "message":
            message = event.get("message", {}) or {}
            message_type = message.get("type")
            text = message.get("text", "")
            if message_type != "text":
                # Keep unsupported message types visible to user.
                text = f"[LINE {message_type}]"
            source_obj = self.build_source(
                chat_id=str(chat_id),
                chat_name=str(chat_id),
                chat_type="group" if source.get("groupId") else "dm",
                user_id=str(user_id),
                user_name=str(user_id),
            )
            msg_event = MessageEvent(
                text=text,
                message_type=MessageType.TEXT,
                source=source_obj,
                raw_message=event,
                message_id=str(message.get("id", "")) or None,
            )
            await self.handle_message(msg_event)
        elif event_type == "postback":
            source_obj = self.build_source(
                chat_id=str(chat_id),
                chat_name=str(chat_id),
                chat_type="group" if source.get("groupId") else "dm",
                user_id=str(user_id),
                user_name=str(user_id),
            )
            data = (event.get("postback", {}) or {}).get("data", "")
            msg_event = MessageEvent(
                text=f"/line_postback {data}",
                message_type=MessageType.COMMAND,
                source=source_obj,
                raw_message=event,
            )
            await self.handle_message(msg_event)
