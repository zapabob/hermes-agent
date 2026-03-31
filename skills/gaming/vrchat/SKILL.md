---
name: vrchat-osc
description: VRChat OSC integration — chatbox messaging, avatar parameter control, and raw OSC via python-osc. Requires VOICEVOX and VRChat running with OSC enabled.
tags: [vrchat, osc, vr, metaverse, chatbox, avatar, voicevox, japanese]
---

# VRChat OSC Integration

## When to use
- User asks to send a message to their VRChat chatbox
- User wants to control VRChat avatar parameters (expressions, gestures, etc.)
- User asks about VRChat status or OSC connectivity
- User wants to change their VRChat avatar
- User wants to automate VRChat interactions from Hermes

## Prerequisites

1. **VRChat must be running** with OSC enabled:
   - VRChat → Settings → OSC → Enable
   - Send port: 9000 (default) — Hermes → VRChat
   - Receive port: 9001 (default) — VRChat → Hermes

2. **python-osc must be installed:**
   ```bash
   uv pip install "hermes-agent[vrchat]"
   # or: pip install python-osc
   ```

3. **Optional config (via .env or environment variables):**
   ```
   VRCHAT_OSC_HOST=127.0.0.1       # VRChat host (default: 127.0.0.1)
   VRCHAT_OSC_SEND_PORT=9000        # Port Hermes sends to VRChat (default: 9000)
   VRCHAT_OSC_RECV_PORT=9001        # Port Hermes listens on (default: 9001)
   ```

## Available Tools

All tools are in `tools/vrchat_osc_tool.py`. Import and call directly in code, or use via the agent.

### `vrchat_chatbox(text, immediate=True)`
Send text to VRChat chatbox (max 144 characters).

```python
from tools.vrchat_osc_tool import vrchat_chatbox
vrchat_chatbox("こんにちは！")
vrchat_chatbox("Hello from Hermes!", immediate=True)
```

### `vrchat_typing(is_typing)`
Show/hide typing indicator in chatbox.

```python
from tools.vrchat_osc_tool import vrchat_typing
vrchat_typing(True)   # show typing
vrchat_typing(False)  # hide typing
```

### `vrchat_avatar_param(name, value)`
Set an avatar OSC parameter (bool, int, or float).

```python
from tools.vrchat_osc_tool import vrchat_avatar_param
vrchat_avatar_param("GestureLeft", 1)       # gesture
vrchat_avatar_param("Viseme", 14)           # mouth shape
vrchat_avatar_param("IsLocal", True)        # bool param
vrchat_avatar_param("MyCustomFloat", 0.75) # float param
```

### `vrchat_avatar_change(avatar_id)`
Request an avatar change.

```python
from tools.vrchat_osc_tool import vrchat_avatar_change
vrchat_avatar_change("avtr_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
```

### `vrchat_send_osc(address, args)`
Send a raw OSC message. For advanced use.

```python
from tools.vrchat_osc_tool import vrchat_send_osc
vrchat_send_osc("/chatbox/input", ["hello", True, False])
vrchat_send_osc("/avatar/parameters/MyParam", [1.0])
```

### `vrchat_status()`
Check if VRChat OSC is reachable.

```python
from tools.vrchat_osc_tool import vrchat_status
print(vrchat_status())
# {"reachable": True, "send_port": 9000, "recv_port": 9001, "host": "127.0.0.1"}
```

## Common Workflows

### Send a greeting to chatbox
```python
from tools.vrchat_osc_tool import vrchat_typing, vrchat_chatbox
import time

vrchat_typing(True)
time.sleep(1)
vrchat_chatbox("Hermesより: こんにちは！")
vrchat_typing(False)
```

### Mirror Hermes response to chatbox (auto-truncate)
```python
from tools.vrchat_osc_tool import vrchat_chatbox

def mirror_to_vrchat(response_text: str):
    MAX = 144
    text = response_text.strip()
    if len(text) > MAX:
        text = text[:MAX - 1] + "…"
    vrchat_chatbox(text)
```

## Notes
- VRChat chatbox limit: **144 characters** (enforced by VRChat OSC spec)
- OSC uses **UDP** — messages may be lost if VRChat is not running; no error is raised
- To use with VOICEVOX: call `vrchat_chatbox()` alongside VOICEVOX TTS for synchronized chat+voice
- The Live2D companion (`live2d-companion` extension) can run alongside Hermes using the same VOICEVOX instance at `http://127.0.0.1:50021`
