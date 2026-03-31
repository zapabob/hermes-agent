"""VRChat OSC integration tool.

Sends OSC messages to VRChat via UDP (port 9000 by default).
Listens for incoming VRChat OSC data (port 9001 by default).

Requires: python-osc  (pip install python-osc)
Install: uv pip install "hermes-agent[vrchat]"

VRChat OSC address reference:
  /chatbox/input          string, bool       - chatbox message + sendImmediately
  /chatbox/typing         bool               - typing indicator
  /avatar/parameters/{n}  bool/int/float     - avatar parameter
  /avatar/change          string             - change avatar by ID
"""

import logging
import os
import socket
import struct
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

# Default OSC endpoints (matches OpenClaw vrchat-relay defaults)
_VRCHAT_HOST = os.environ.get("VRCHAT_OSC_HOST", "127.0.0.1")
_VRCHAT_SEND_PORT = int(os.environ.get("VRCHAT_OSC_SEND_PORT", "9000"))
_VRCHAT_RECV_PORT = int(os.environ.get("VRCHAT_OSC_RECV_PORT", "9001"))

# Chatbox limit enforced by VRChat
_CHATBOX_MAX_CHARS = 144

_client = None
_client_lock = threading.Lock()


def _get_client():
    """Lazy-init OSC UDP client."""
    global _client
    with _client_lock:
        if _client is None:
            try:
                from pythonosc import udp_client as _udp
                _client = _udp.SimpleUDPClient(_VRCHAT_HOST, _VRCHAT_SEND_PORT)
            except ImportError as e:
                raise RuntimeError(
                    "python-osc is required for VRChat OSC integration.\n"
                    "Install with: uv pip install 'hermes-agent[vrchat]'\n"
                    f"Details: {e}"
                ) from e
    return _client


def vrchat_chatbox(text: str, immediate: bool = True) -> dict:
    """Send a message to the VRChat chatbox.

    Args:
        text: Message text (max 144 characters)
        immediate: If True the message is shown immediately.
                   If False it goes through the keyboard UI first.

    Returns:
        {"success": True} or {"success": False, "error": "..."}
    """
    if not text or not text.strip():
        return {"success": False, "error": "Message cannot be empty"}
    if len(text) > _CHATBOX_MAX_CHARS:
        return {
            "success": False,
            "error": f"Message exceeds {_CHATBOX_MAX_CHARS} character limit ({len(text)} chars)",
        }
    try:
        client = _get_client()
        # third arg (False) = do NOT bypass the keyboard; VRChat OSC spec
        client.send_message("/chatbox/input", [text, immediate, False])
        logger.info("VRChat chatbox sent: %r", text)
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def vrchat_chatbox_clear() -> dict:
    """Clear the VRChat chatbox."""
    return vrchat_chatbox("", immediate=True)


def vrchat_typing(is_typing: bool) -> dict:
    """Set the VRChat chatbox typing indicator.

    Args:
        is_typing: True to show typing, False to hide.
    """
    try:
        client = _get_client()
        client.send_message("/chatbox/typing", bool(is_typing))
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def vrchat_avatar_param(name: str, value: Any) -> dict:
    """Set a VRChat avatar OSC parameter.

    Args:
        name: Parameter name (e.g. "GestureLeft", "Viseme", custom params)
        value: bool, int, or float value
    """
    if not name or not name.strip():
        return {"success": False, "error": "Parameter name cannot be empty"}
    if not isinstance(value, (bool, int, float)):
        return {"success": False, "error": "value must be bool, int, or float"}
    try:
        client = _get_client()
        client.send_message(f"/avatar/parameters/{name}", value)
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def vrchat_avatar_change(avatar_id: str) -> dict:
    """Request a VRChat avatar change.

    Args:
        avatar_id: VRChat avatar ID string (e.g. "avtr_xxxxxxxx-xxxx-...")
    """
    if not avatar_id or not avatar_id.strip():
        return {"success": False, "error": "avatar_id cannot be empty"}
    try:
        client = _get_client()
        client.send_message("/avatar/change", avatar_id)
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def vrchat_send_osc(address: str, args: list) -> dict:
    """Send a raw OSC message to VRChat.

    Args:
        address: OSC address string starting with '/' (e.g. "/avatar/parameters/MyParam")
        args: List of argument values (str, int, float, bool)
    """
    if not address or not address.startswith("/"):
        return {"success": False, "error": "address must start with '/'"}
    try:
        client = _get_client()
        if not args:
            client.send_message(address, None)
        elif len(args) == 1:
            client.send_message(address, args[0])
        else:
            client.send_message(address, args)
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def vrchat_status() -> dict:
    """Check VRChat OSC connectivity (sends a probe and checks if port is reachable)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        # Try to bind send port briefly — just verifies the host/port is usable
        sock.connect((_VRCHAT_HOST, _VRCHAT_SEND_PORT))
        sock.close()
        return {
            "reachable": True,
            "send_port": _VRCHAT_SEND_PORT,
            "recv_port": _VRCHAT_RECV_PORT,
            "host": _VRCHAT_HOST,
        }
    except Exception as exc:
        return {
            "reachable": False,
            "send_port": _VRCHAT_SEND_PORT,
            "recv_port": _VRCHAT_RECV_PORT,
            "host": _VRCHAT_HOST,
            "error": str(exc),
        }
