"""VRChat OSC controller — chatbox, params, actions, emotion."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pythonosc import dispatcher, osc_server, udp_client

ROOT = Path(__file__).parent
_PARAM_MAP_PATH = ROOT / "osc_param_map.json"


def load_param_map() -> dict:
    if _PARAM_MAP_PATH.exists():
        return json.loads(_PARAM_MAP_PATH.read_text(encoding="utf-8"))
    return {"emotions": {}, "actions": {}, "voicevox_emotions": {}}


class OSCController:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9000,
        param_map: dict | None = None,
    ) -> None:
        self._client = udp_client.SimpleUDPClient(host, port)
        self._map = param_map or load_param_map()

    def send_chatbox(self, text: str, immediate: bool = True, sfx: bool = True) -> None:
        """Send text to VRChat chatbox with advanced flags."""
        self._client.send_message("/chatbox/input", [text, immediate, sfx])

    def set_typing(self, typing: bool) -> None:
        """Set the VRChat typing indicator."""
        address = self._map.get("chatbox", {}).get("typing", "/chatbox/typing")
        self._client.send_message(address, typing)

    def send_tracking(self, name: str, value: Any) -> None:
        """Send tracking or avatar data (eye closed, head pos, etc.)."""
        address = self._map.get("tracking", {}).get(name, name)
        self._client.send_message(address, value)

    def set_param(self, name: str, value: Any) -> None:
        """Set a single avatar parameter."""
        self._client.send_message(f"/avatar/parameters/{name}", value)

    def send_action(self, action: str, value: Any = 1.0) -> None:
        """Send a VRChat input action (jump, move, etc.)."""
        address = self._map.get("actions", {}).get(action, f"/input/{action}")
        # Some inputs like Jump/Run/Voice prefer int(1 or 0)
        if any(x in address.lower() for x in ["jump", "run", "voice", "mute"]):
            value = int(value)
        self._client.send_message(address, value)

    def apply_emotion(self, emotion: str) -> None:
        """Send all OSC params for a named emotion. Falls back to neutral."""
        emotions = self._map.get("emotions", {})
        params = emotions.get(emotion) or emotions.get("neutral") or {}
        for param_name, param_value in params.items():
            self.set_param(param_name, param_value)


class OSCListener:
    """Listens for VRChat OSC telemetry on port 9001."""
    def __init__(self, host: str = "127.0.0.1", port: int = 9001):
        self.host = host
        self.port = port
        self.dispatcher = dispatcher.Dispatcher()
        self.telemetry: dict[str, Any] = {}
        self._server = None
        
        # Default handlers
        self.dispatcher.map("/avatar/change", self._handle_avatar_change)
        self.dispatcher.set_default_handler(self._handle_generic)

    def _handle_avatar_change(self, address: str, *args: Any):
        avatar_id = args[0] if args else "unknown"
        self.telemetry["avatar_id"] = avatar_id
        logging.info(f"VRChat Avatar Changed: {avatar_id}")

    def _handle_generic(self, address: str, *args: Any):
        # Store latest value for any address (e.g. visemes, parameters)
        self.telemetry[address] = args[0] if args else None

    def start(self):
        self._server = osc_server.ThreadingOSCUDPServer(
            (self.host, self.port), self.dispatcher
        )
        logging.info(f"OSC Listener started on {self.host}:{self.port}")
        self._server.serve_forever()

    def stop(self):
        if self._server:
            logging.info("Stopping OSC Listener...")
            self._server.shutdown()
            self._server.server_close()
            self._server = None
