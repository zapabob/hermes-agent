"""SillyTavern server management plugin for Hermes.

Tools:
  sillytavern_status  - check whether the local SillyTavern server responds
  sillytavern_start   - configure from Hermes providers, then launch server
  sillytavern_stop    - stop the server process
  sillytavern_version - report installed version from package.json

Auto-configures secrets.json and settings.json from Hermes .env / config.yaml
so the local llama server and cloud API keys (OpenAI, Gemini) are available.
"""

import json
import os
import subprocess
import urllib.request
from pathlib import Path

_HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))

DEFAULT_DIR = None  # resolved on first use


def _resolve_dir() -> str:
    env = os.environ.get("SILLYTAVERN_DIR")
    if env:
        return env
    # Repo submodule checkout
    sub = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "vendor",
        "SillyTavern",
    )
    if os.path.isfile(os.path.join(sub, "server.js")):
        return sub
    # Local install fallback.  Keep this portable and do not embed a user's
    # Windows profile name in the bundled plugin.
    return os.path.join(os.path.expanduser("~"), "Documents", "SillyTavern")


def _get_dir() -> str:
    global DEFAULT_DIR
    if DEFAULT_DIR is None:
        DEFAULT_DIR = _resolve_dir()
    return DEFAULT_DIR


DEFAULT_HOST = os.environ.get("SILLYTAVERN_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("SILLYTAVERN_PORT", "8000"))
_LOCAL_LLAMA = "http://127.0.0.1:8080/v1"

_STATE: dict = {"proc": None}


def _base_url() -> str:
    return f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"


def _is_up(timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(_base_url() + "/", timeout=timeout) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def _installed() -> bool:
    return os.path.isfile(os.path.join(_get_dir(), "server.js"))


# ── Auto-configuration from Hermes secrets ──────────────────────────

def _load_hermes_env() -> dict:
    """Read ~/.hermes/.env and return a key-value dict."""
    env_path = _HERMES_HOME / ".env"
    if not env_path.exists():
        return {}
    keys = {}
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                keys[k] = v
    return keys


def _configure() -> dict:
    """Write secrets.json and settings.json for SillyTavern.

    Returns a dict summarising which secrets were written (key names only).
    """
    st_dir = _get_dir()
    data_dir = os.path.join(st_dir, "data", "default-user")
    os.makedirs(data_dir, exist_ok=True)

    env = _load_hermes_env()

    # ── secrets.json ────────────────────────────────────────────────
    secrets_path = os.path.join(data_dir, "secrets.json")
    existing = {}
    if os.path.exists(secrets_path):
        with open(secrets_path, encoding="utf-8-sig") as f:
            existing = json.load(f)

    secret_map = {
        "api_key_openai": env.get("OPENAI_API_KEY", ""),
        "api_key_makersuite": env.get("GEMINI_API_KEY", ""),
        "api_key_xai": env.get("XAI_API_KEY", ""),
        "api_key_llamacpp": "local",
    }
    written = []
    for key, val in secret_map.items():
        if val and key not in existing:
            existing[key] = val
            written.append(key)

    if written:
        with open(secrets_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

    # ── settings.json ───────────────────────────────────────────────
    settings_path = os.path.join(data_dir, "settings.json")
    settings = {}
    if os.path.exists(settings_path):
        with open(settings_path, encoding="utf-8-sig") as f:
            settings = json.load(f)

    changed = []
    oai = settings.get("oai_settings", {})

    # Set primary API to local llama
    if settings.get("main_api") != "openai":
        settings["main_api"] = "openai"
        changed.append("main_api")

    if settings.get("api_server") != _LOCAL_LLAMA:
        settings["api_server"] = _LOCAL_LLAMA
        changed.append("api_server")

    if settings.get("max_context") != 65536:
        settings["max_context"] = 65536
        changed.append("max_context")

    # OpenAI-compatible settings for local llama
    if oai.get("chat_completion_source") != "openai":
        oai["chat_completion_source"] = "openai"
        changed.append("oai.chat_completion_source")

    if oai.get("reverse_proxy") != _LOCAL_LLAMA:
        oai["reverse_proxy"] = _LOCAL_LLAMA
        changed.append("oai.reverse_proxy")

    if oai.get("openai_model") != "Qwen3.6-35B-A3B-Uncensored-IQ3_M":
        oai["openai_model"] = "Qwen3.6-35B-A3B-Uncensored-IQ3_M"
        changed.append("oai.model")

    if oai.get("openai_max_context") != 65536:
        oai["openai_max_context"] = 65536
        changed.append("oai.max_context")

    if oai.get("openai_max_tokens") != 8192:
        oai["openai_max_tokens"] = 8192
        changed.append("oai.max_tokens")

    if not oai.get("stream_openai"):
        oai["stream_openai"] = True
        changed.append("oai.stream")

    settings["oai_settings"] = oai

    # Unlock max context
    pu = settings.get("power_user", {})
    if not pu.get("max_context_unlocked"):
        pu["max_context_unlocked"] = True
        changed.append("power_user.max_context_unlocked")
    settings["power_user"] = pu

    # Configure SillyTavern's built-in OpenAI Compatible TTS provider to use
    # the loopback Hakua bridge. The bridge keeps Fish Audio credentials server-side.
    extension_settings = settings.setdefault("extension_settings", {})
    tts = extension_settings.setdefault("tts", {})
    bridge_url = os.environ.get("HAKUA_TTS_BRIDGE_URL", "http://127.0.0.1:8765/v1/audio/speech")
    tts_updates = {
        "ttsEnabled": True,
        "currentProvider": "OpenAI Compatible",
        "OpenAI Compatible": {
            "provider_endpoint": bridge_url,
            "model": "hakua",
            "speed": 1,
            "available_voices": ["hakua"],
            "voiceMap": {},
        },
    }
    for key, value in tts_updates.items():
        if tts.get(key) != value:
            tts[key] = value
            changed.append(f"extension_settings.tts.{key}")

    if changed:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    return {"secrets_written": written, "settings_changed": changed}


# ── Tool handlers ───────────────────────────────────────────────────

def sillytavern_status(args, **kwargs) -> str:
    return json.dumps(
        {
            "installed": _installed(),
            "install_dir": _get_dir(),
            "url": _base_url(),
            "running": _is_up(),
        }
    )


def sillytavern_start(args, **kwargs) -> str:
    if not _installed():
        return json.dumps(
            {"ok": False, "error": f"server.js not found in {_get_dir()}"}
        )
    if _is_up():
        return json.dumps(
            {"ok": True, "already_running": True, "url": _base_url()}
        )

    # Auto-configure from Hermes before launch
    config_result = _configure()
    config_note = (
        f"secrets: {len(config_result['secrets_written'])} new, "
        f"settings: {len(config_result['settings_changed'])} changed"
    )

    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    proc = subprocess.Popen(
        [
            "node",
            "server.js",
            "--browserLaunchEnabled",
            "false",
            "--port",
            str(DEFAULT_PORT),
        ],
        cwd=_get_dir(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    _STATE["proc"] = proc
    import time

    for _ in range(45):
        time.sleep(1)
        if _is_up():
            return json.dumps(
                {
                    "ok": True,
                    "pid": proc.pid,
                    "url": _base_url(),
                    "config": config_note,
                }
            )
    return json.dumps(
        {
            "ok": False,
            "pid": proc.pid,
            "error": "did not become ready in 45s",
            "config": config_note,
        }
    )


def sillytavern_stop(args, **kwargs) -> str:
    proc = _STATE.get("proc")
    if proc and proc.poll() is None:
        proc.terminate()
        _STATE["proc"] = None
        return json.dumps({"ok": True, "stopped_pid": proc.pid})
    # Fallback: find the PID bound to the port (Windows)
    try:
        out = subprocess.check_output(
            ["netstat", "-ano", "-p", "tcp"],
            text=True,
            encoding="cp932",
            errors="replace",
            timeout=15,
        )
        pids = {
            line.split()[-1]
            for line in out.splitlines()
            if f":{DEFAULT_PORT}" in line and "LISTENING" in line
        }
        for pid in pids:
            subprocess.run(
                ["taskkill", "/PID", pid, "/F"],
                capture_output=True,
                stdin=subprocess.DEVNULL,
            )
        return json.dumps({"ok": True, "killed_pids": sorted(pids)})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def sillytavern_version(args, **kwargs) -> str:
    try:
        with open(os.path.join(_get_dir(), "package.json"), encoding="utf-8") as f:
            pkg = json.load(f)
        return json.dumps({"ok": True, "version": pkg.get("version")})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def sillytavern_configure(args, **kwargs) -> str:
    """Explicitly re-run auto-configuration."""
    result = _configure()
    return json.dumps({"ok": True, **result})


# ── Import SillyTavern data into Hermes memory ──────────────────────

def _scan_data() -> dict:
    """Run st_import.scan() against the resolved install dir."""
    import importlib.util

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "st_import.py")
    spec = importlib.util.spec_from_file_location("st_import", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.scan(_get_dir())


def sillytavern_scan(args, **kwargs) -> str:
    """Summarise importable SillyTavern data (characters, chats, lorebooks)."""
    try:
        data = _scan_data()
        summary = {
            "ok": True,
            "characters": [
                {"name": c.get("name"), "file": c.get("_file")}
                for c in data["characters"]
            ],
            "chats": [
                {
                    "character": c["character"],
                    "file": c["file"],
                    "messages": c["message_count"],
                }
                for c in data["chats"]
            ],
            "lorebooks": [
                {"name": lb.get("name"), "entries": lb.get("entry_count")}
                for lb in data["lorebooks"]
            ],
        }
        return json.dumps(summary, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def sillytavern_import_memory(args, **kwargs) -> str:
    """Emit SillyTavern data as memory records for Hermes to ingest.

    Returns a list of {content, tags, salience} entries. The agent decides
    which to persist via its own memory/ebbinghaus tools; this handler only
    extracts and formats — it does not write to any store directly.
    """
    try:
        data = _scan_data()
        records = []

        for c in data["characters"]:
            name = c.get("name", "")
            parts = []
            for field in ("description", "personality", "scenario", "first_mes"):
                val = str(c.get(field, "")).strip()
                if val and val != name:
                    parts.append(f"{field}: {val}")
            if name and parts:
                records.append(
                    {
                        "content": f"SillyTavern character '{name}': " + " | ".join(parts),
                        "tags": "sillytavern,character," + name,
                        "salience": 0.7,
                    }
                )

        for lb in data["lorebooks"]:
            for entry in lb.get("entries", []):
                content = str(entry.get("content", "")).strip()
                keys = ",".join(entry.get("keys", []))
                if content:
                    records.append(
                        {
                            "content": f"Lorebook '{lb['name']}' [{keys}]: {content[:800]}",
                            "tags": f"sillytavern,lorebook,{lb['name']}",
                            "salience": 0.6,
                        }
                    )

        for chat in data["chats"]:
            msgs = chat.get("messages", [])
            if not msgs:
                continue
            convo = "\n".join(
                f"{m['name']}: {m['mes']}" for m in msgs if m.get("mes")
            )
            records.append(
                {
                    "content": (
                        f"SillyTavern chat with '{chat['character']}' "
                        f"({chat['message_count']} msgs): {convo[:1500]}"
                    ),
                    "tags": f"sillytavern,chat,{chat['character']}",
                    "salience": 0.5,
                }
            )

        return json.dumps(
            {"ok": True, "record_count": len(records), "records": records},
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── Codex / xAI reverse-proxy bridge ────────────────────────────────

_PROXY_PORT = int(os.environ.get("SILLYTAVERN_PROXY_PORT", "8199"))
_PROXY_STATE: dict = {"proc": None}


def _proxy_up(timeout: float = 2.0) -> bool:
    try:
        # Any response (even 401/404) means the listener is alive.
        urllib.request.urlopen(
            f"http://127.0.0.1:{_PROXY_PORT}/", timeout=timeout
        )
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def _codex_token_valid() -> dict:
    """Return {present, expired, exp} for the Codex OAuth access token."""
    auth_path = os.path.expanduser("~/.codex/auth.json")
    if not os.path.exists(auth_path):
        return {"present": False}
    try:
        with open(auth_path, encoding="utf-8") as f:
            auth = json.load(f)
        tok = (auth.get("tokens") or {}).get("access_token", "")
        if not tok:
            return {"present": False}
        import base64 as _b64
        import time as _time

        payload = tok.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(_b64.urlsafe_b64decode(payload))
        exp = claims.get("exp", 0)
        return {
            "present": True,
            "expired": exp < _time.time(),
            "exp": exp,
        }
    except Exception as exc:
        return {"present": True, "error": str(exc)}


def sillytavern_proxy_start(args, **kwargs) -> str:
    """Start the local Codex/xAI reverse-proxy for SillyTavern."""
    if _proxy_up():
        return json.dumps(
            {
                "ok": True,
                "already_running": True,
                "port": _PROXY_PORT,
                "routes": {
                    "codex": f"http://127.0.0.1:{_PROXY_PORT}/codex/v1",
                    "xai": f"http://127.0.0.1:{_PROXY_PORT}/xai/v1",
                    "llama": f"http://127.0.0.1:{_PROXY_PORT}/llama/v1",
                },
            }
        )
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codex_proxy.py")
    import sys as _sys

    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    proc = subprocess.Popen(
        [_sys.executable, script, "--port", str(_PROXY_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    _PROXY_STATE["proc"] = proc
    import time

    for _ in range(10):
        time.sleep(0.5)
        if _proxy_up():
            return json.dumps(
                {
                    "ok": True,
                    "pid": proc.pid,
                    "port": _PROXY_PORT,
                    "codex_token": _codex_token_valid(),
                    "routes": {
                        "codex": f"http://127.0.0.1:{_PROXY_PORT}/codex/v1",
                        "xai": f"http://127.0.0.1:{_PROXY_PORT}/xai/v1",
                        "llama": f"http://127.0.0.1:{_PROXY_PORT}/llama/v1",
                    },
                }
            )
    return json.dumps({"ok": False, "pid": proc.pid, "error": "proxy not ready in 5s"})


def sillytavern_proxy_stop(args, **kwargs) -> str:
    """Stop the local Codex/xAI reverse-proxy."""
    proc = _PROXY_STATE.get("proc")
    if proc and proc.poll() is None:
        proc.terminate()
        _PROXY_STATE["proc"] = None
        return json.dumps({"ok": True, "stopped_pid": proc.pid})
    try:
        out = subprocess.check_output(
            ["netstat", "-ano", "-p", "tcp"],
            text=True,
            encoding="cp932",
            errors="replace",
            timeout=15,
        )
        pids = {
            line.split()[-1]
            for line in out.splitlines()
            if f":{_PROXY_PORT}" in line and "LISTENING" in line
        }
        for pid in pids:
            subprocess.run(
                ["taskkill", "/PID", pid, "/F"],
                capture_output=True,
                stdin=subprocess.DEVNULL,
            )
        return json.dumps({"ok": True, "killed_pids": sorted(pids)})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def sillytavern_proxy_status(args, **kwargs) -> str:
    """Report proxy state and Codex token validity."""
    return json.dumps(
        {
            "running": _proxy_up(),
            "port": _PROXY_PORT,
            "codex_token": _codex_token_valid(),
            "routes": {
                "codex": f"http://127.0.0.1:{_PROXY_PORT}/codex/v1",
                "xai": f"http://127.0.0.1:{_PROXY_PORT}/xai/v1",
                "llama": f"http://127.0.0.1:{_PROXY_PORT}/llama/v1",
            },
        }
    )


# ── ST-native features (characters/sessions/lore/persona) ───────────

def _native():
    import importlib.util

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "st_native.py")
    spec = importlib.util.spec_from_file_location("st_native", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def st_character_create(args, **kwargs) -> str:
    try:
        n = _native()
        cid = n.create_character(
            args.get("name", "Character"),
            description=args.get("description", ""),
            personality=args.get("personality", ""),
            scenario=args.get("scenario", ""),
            first_mes=args.get("first_mes", ""),
            system_prompt=args.get("system_prompt", ""),
        )
        return json.dumps({"ok": True, "character_id": cid})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def st_character_list(args, **kwargs) -> str:
    try:
        return json.dumps({"ok": True, "characters": _native().list_characters()},
                          ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def st_persona_create(args, **kwargs) -> str:
    try:
        pid = _native().create_persona(
            args.get("name", "User"),
            description=args.get("description", ""),
            is_default=bool(args.get("is_default", True)),
        )
        return json.dumps({"ok": True, "persona_id": pid})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def st_lore_add(args, **kwargs) -> str:
    try:
        lid = _native().add_lore(
            args.get("book", "default"),
            args.get("keys", []),
            args.get("content", ""),
            enabled=bool(args.get("enabled", True)),
        )
        return json.dumps({"ok": True, "lore_id": lid})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def st_session_start(args, **kwargs) -> str:
    try:
        sid = _native().create_session(
            args.get("character_id"),
            persona_id=args.get("persona_id"),
            title=args.get("title", ""),
        )
        return json.dumps({"ok": True, "session_id": sid})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def st_session_say(args, **kwargs) -> str:
    """Add a user turn and return the assembled ST-style prompt to answer it."""
    try:
        n = _native()
        sid = args.get("session_id")
        user_msg = args.get("message", "")
        n.add_message(sid, "user", user_msg, name=args.get("user_name", ""))
        prompt = n.build_prompt(
            sid, user_msg, lore_book=args.get("lore_book"),
            history_limit=int(args.get("history_limit", 20)),
        )
        return json.dumps({"ok": True, **prompt}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def st_session_reply(args, **kwargs) -> str:
    """Record the character's reply message into the session."""
    try:
        n = _native()
        mid = n.add_message(
            args.get("session_id"), "assistant",
            args.get("content", ""), name=args.get("character_name", ""),
        )
        return json.dumps({"ok": True, "message_id": mid})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def st_session_summary(args, **kwargs) -> str:
    try:
        _native().set_summary(args.get("session_id"), args.get("summary", ""))
        return json.dumps({"ok": True})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def st_session_to_memory(args, **kwargs) -> str:
    """Emit memory records from a session for Hermes ebbinghaus ingestion."""
    try:
        recs = _native().session_to_memory_records(args.get("session_id"))
        return json.dumps({"ok": True, "record_count": len(recs), "records": recs},
                          ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def st_memory_to_lore(args, **kwargs) -> str:
    """Ingest Hermes memory records into a lorebook (keys from tags)."""
    try:
        added = _native().import_memory_to_lore(
            args.get("book", "memory"), args.get("records", []),
        )
        return json.dumps({"ok": True, "added": added})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── Voice Roleplay: STT → ST-native → TTS → Memory ──────────────────

def st_voice_roleplay(args, **kwargs) -> str:
    """
    Voice roleplay turn (phase 1):
    1. Record audio from microphone (duration_seconds)
    2. STT transcribe (faster-whisper local)
    3. ST-native: add user message, build prompt with lore
    4. Return prompt for the agent to complete via LLM
    """
    try:
        n = _native()
        session_id = args.get("session_id")
        duration = int(args.get("duration_seconds", 10))
        lore_book = args.get("lore_book")
        history_limit = int(args.get("history_limit", 20))
        tts_voice = args.get("tts_voice", "hakua")
        tts_model = args.get("tts_model", "irodori-tts")
        tts_speed = float(args.get("tts_speed", 1.0))
        stt_model = args.get("stt_model", "base")
        auto_memory = bool(args.get("auto_memory", True))

        # Step 1: Record audio using AudioRecorder
        from tools.voice_mode import create_audio_recorder
        recorder = create_audio_recorder()
        recorder.start()
        import time
        time.sleep(duration)
        wav_path = recorder.stop()
        if not wav_path:
            return json.dumps({"ok": False, "error": "Failed to record audio or recording too short/quiet"})

        # Step 2: STT transcribe
        from tools.voice_mode import transcribe_recording
        stt_result = transcribe_recording(wav_path, model=stt_model)
        if not stt_result.get("success"):
            return json.dumps({"ok": False, "error": f"STT failed: {stt_result.get('error')}"})
        transcript = stt_result.get("transcript", "").strip()
        if not transcript:
            return json.dumps({"ok": False, "error": "No speech detected"})

        # Step 3: Add user message and build ST-native prompt
        n.add_message(session_id, "user", transcript, name="User")
        prompt = n.build_prompt(
            session_id, transcript, lore_book=lore_book, history_limit=history_limit
        )

        # Return the prompt for the agent to complete via LLM
        return json.dumps({
            "ok": True,
            "stage": "prompt_ready",
            "transcript": transcript,
            "prompt": prompt,
            "tts_voice": tts_voice,
            "tts_model": tts_model,
            "tts_speed": tts_speed,
            "auto_memory": auto_memory,
        }, ensure_ascii=False)

    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


def st_voice_roleplay_complete(args, **kwargs) -> str:
    """
    Voice roleplay turn (phase 2) - complete after LLM generates reply:
    1. Record assistant reply into session
    2. TTS synthesize with irodori (hakua voice)
    3. Play audio
    4. If auto_memory: emit session to ebbinghaus memory
    """
    try:
        n = _native()
        session_id = args.get("session_id")
        reply_content = args.get("reply_content", "")
        tts_voice = args.get("tts_voice", "hakua")
        tts_model = args.get("tts_model", "irodori-tts")
        tts_speed = float(args.get("tts_speed", 1.0))
        auto_memory = bool(args.get("auto_memory", True))

        # Record the assistant's reply
        n.add_message(session_id, "assistant", reply_content, name="Character")

        # Step 2: TTS with irodori (hakua voice)
        # Use the text_to_speech_tool which routes to irodori provider
        from tools.tts_tool import text_to_speech_tool
        # Let text_to_speech_tool handle output path (it manages temp dir)
        tts_result = text_to_speech_tool(text=reply_content)

        # Step 3: Play audio
        from tools.voice_mode import play_audio_file
        tts_file = tts_result.get("file_path") if isinstance(tts_result, dict) else None
        if tts_file and os.path.isfile(tts_file) and os.path.getsize(tts_file) > 0:
            play_audio_file(tts_file)

        # Step 4: Memory bridge
        memory_records = None
        if auto_memory:
            memory_records = n.session_to_memory_records(session_id)
            # Note: actual ebbinghaus ingestion is done by agent via memory tool

        return json.dumps({
            "ok": True,
            "tts_file": tts_file,
            "memory_records": memory_records if auto_memory else None,
        }, ensure_ascii=False)

    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── Audio landing: copy audio files into SillyTavern uploads ──────────

def _st_uploads_dir() -> str:
    """Return the SillyTavern uploads directory path."""
    st_dir = _get_dir()
    return os.path.join(st_dir, "data", "_uploads")


def sillytavern_audio_land(args: dict | None = None, **kwargs) -> str:
    """Copy the latest audio file or zip into SillyTavern's data/_uploads/ directory."""
    try:
        source_path = (args or kwargs).get("source_path", "")
        target_name = (args or kwargs).get("target_name", "")
        uploads = _st_uploads_dir()
        os.makedirs(uploads, exist_ok=True)

        if not source_path:
            # Auto-detect: find the latest zip or wav in the irodori buffer
            try:
                from plugins.irodori_tts.audio_buffer import (
                    _buffer_dir_from_config,
                    buffer_status as _buffer_status,
                )

                buf_dir = _buffer_dir_from_config()
                candidates = []
                for ext in (".zip", "*.wav"):
                    if ext.endswith(".wav"):
                        candidates += sorted(
                            Path(buf_dir).glob("*.wav"),
                            key=lambda p: p.stat().st_mtime,
                            reverse=True,
                        )
                    elif ext.endswith(".zip"):
                        candidates += sorted(
                            Path(buf_dir).glob("audio-*.zip"),
                            key=lambda p: p.stat().st_mtime,
                            reverse=True,
                        )
                if not candidates:
                    return json.dumps(
                        {"ok": False, "error": "No audio files or zips found in irodori buffer."}
                    )
                source_path = str(candidates[0])
            except Exception as exc:
                return json.dumps(
                    {"ok": False, "error": f"Could not auto-detect source: {exc}"}
                )

        src = Path(source_path)
        if not src.exists():
            return json.dumps(
                {"ok": False, "error": f"Source file not found: {source_path}"}
            )

        dest_name = target_name or src.name
        dest = Path(uploads) / dest_name
        import shutil
        shutil.copy2(src, dest)
        return json.dumps(
            {
                "ok": True,
                "source": str(src),
                "dest": str(dest),
                "uploads_dir": uploads,
                "st_url": f"{_base_url()}/uploads/{dest_name}",
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


# ── Register ────────────────────────────────────────────────────────

def register(ctx):
    empty = {"type": "object", "properties": {}}
    ctx.register_tool(
        name="sillytavern_status",
        toolset="sillytavern",
        description="Check whether the local SillyTavern server is installed and running.",
        schema=empty,
        handler=sillytavern_status,
        check_fn=_installed,
    )
    ctx.register_tool(
        name="sillytavern_start",
        toolset="sillytavern",
        description="Start SillyTavern (auto-configures secrets/settings from Hermes).",
        schema=empty,
        handler=sillytavern_start,
        check_fn=_installed,
    )
    ctx.register_tool(
        name="sillytavern_stop",
        toolset="sillytavern",
        description="Stop the local SillyTavern server.",
        schema=empty,
        handler=sillytavern_stop,
        check_fn=_installed,
    )
    ctx.register_tool(
        name="sillytavern_version",
        toolset="sillytavern",
        description="Report the installed SillyTavern version.",
        schema=empty,
        handler=sillytavern_version,
        check_fn=_installed,
    )
    ctx.register_tool(
        name="sillytavern_configure",
        toolset="sillytavern",
        description="(Re-)run auto-configuration: sync Hermes API keys and settings into SillyTavern.",
        schema=empty,
        handler=sillytavern_configure,
        check_fn=_installed,
    )
    ctx.register_tool(
        name="sillytavern_scan",
        toolset="sillytavern",
        description="List importable SillyTavern data (characters, chats, lorebooks).",
        schema=empty,
        handler=sillytavern_scan,
        check_fn=_installed,
    )
    ctx.register_tool(
        name="sillytavern_import_memory",
        toolset="sillytavern",
        description="Extract SillyTavern characters/chats/lorebooks as memory records for Hermes to ingest.",
        schema=empty,
        handler=sillytavern_import_memory,
        check_fn=_installed,
    )
    ctx.register_tool(
        name="sillytavern_proxy_start",
        toolset="sillytavern",
        description="Start local reverse-proxy so SillyTavern can use Codex OAuth and xAI Grok.",
        schema=empty,
        handler=sillytavern_proxy_start,
    )
    ctx.register_tool(
        name="sillytavern_proxy_stop",
        toolset="sillytavern",
        description="Stop the Codex/xAI reverse-proxy.",
        schema=empty,
        handler=sillytavern_proxy_stop,
    )
    ctx.register_tool(
        name="sillytavern_proxy_status",
        toolset="sillytavern",
        description="Report Codex/xAI proxy state and Codex OAuth token validity.",
        schema=empty,
        handler=sillytavern_proxy_status,
    )
    # ── ST-native roleplay features (no ST server needed) ──
    ctx.register_tool(
        name="st_character_create",
        toolset="sillytavern",
        description="Create a roleplay character (name/description/personality/scenario/first_mes).",
        schema={"type": "object", "properties": {
            "name": {"type": "string"}, "description": {"type": "string"},
            "personality": {"type": "string"}, "scenario": {"type": "string"},
            "first_mes": {"type": "string"}, "system_prompt": {"type": "string"},
        }, "required": ["name"]},
        handler=st_character_create,
    )
    ctx.register_tool(
        name="st_character_list",
        toolset="sillytavern",
        description="List stored roleplay characters.",
        schema=empty,
        handler=st_character_list,
    )
    ctx.register_tool(
        name="st_persona_create",
        toolset="sillytavern",
        description="Create a user persona (who the user is in roleplay).",
        schema={"type": "object", "properties": {
            "name": {"type": "string"}, "description": {"type": "string"},
            "is_default": {"type": "boolean"},
        }, "required": ["name"]},
        handler=st_persona_create,
    )
    ctx.register_tool(
        name="st_lore_add",
        toolset="sillytavern",
        description="Add a lorebook/world-info entry with keyword triggers.",
        schema={"type": "object", "properties": {
            "book": {"type": "string"}, "keys": {"type": "array", "items": {"type": "string"}},
            "content": {"type": "string"}, "enabled": {"type": "boolean"},
        }, "required": ["book", "content"]},
        handler=st_lore_add,
    )
    ctx.register_tool(
        name="st_session_start",
        toolset="sillytavern",
        description="Start a roleplay chat session for a character (seeds first_mes).",
        schema={"type": "object", "properties": {
            "character_id": {"type": "integer"}, "persona_id": {"type": "integer"},
            "title": {"type": "string"},
        }, "required": ["character_id"]},
        handler=st_session_start,
    )
    ctx.register_tool(
        name="st_session_say",
        toolset="sillytavern",
        description="Add a user turn and get the assembled ST-style prompt (system+lore+history).",
        schema={"type": "object", "properties": {
            "session_id": {"type": "integer"}, "message": {"type": "string"},
            "lore_book": {"type": "string"}, "history_limit": {"type": "integer"},
            "user_name": {"type": "string"},
        }, "required": ["session_id", "message"]},
        handler=st_session_say,
    )
    ctx.register_tool(
        name="st_session_reply",
        toolset="sillytavern",
        description="Record the character's generated reply into the session.",
        schema={"type": "object", "properties": {
            "session_id": {"type": "integer"}, "content": {"type": "string"},
            "character_name": {"type": "string"},
        }, "required": ["session_id", "content"]},
        handler=st_session_reply,
    )
    ctx.register_tool(
        name="st_session_summary",
        toolset="sillytavern",
        description="Set/update the running summary for a roleplay session.",
        schema={"type": "object", "properties": {
            "session_id": {"type": "integer"}, "summary": {"type": "string"},
        }, "required": ["session_id", "summary"]},
        handler=st_session_summary,
    )
    ctx.register_tool(
        name="st_session_to_memory",
        toolset="sillytavern",
        description="Emit session summary/chat as memory records for Hermes ebbinghaus ingestion.",
        schema={"type": "object", "properties": {
            "session_id": {"type": "integer"},
        }, "required": ["session_id"]},
        handler=st_session_to_memory,
    )
    ctx.register_tool(
        name="st_memory_to_lore",
        toolset="sillytavern",
        description="Ingest Hermes memory records into a lorebook (tags become keyword triggers).",
        schema={"type": "object", "properties": {
            "book": {"type": "string"},
            "records": {"type": "array", "items": {"type": "object"}},
        }, "required": ["book", "records"]},
        handler=st_memory_to_lore,
    )
    # Voice Roleplay: STT -> ST-native -> TTS -> Memory
    ctx.register_tool(
        name="st_voice_roleplay",
        toolset="sillytavern",
        description="Voice roleplay turn (phase 1): record audio -> STT -> ST-native prompt assembly. Returns prompt for LLM completion.",
        schema={"type": "object", "properties": {
            "session_id": {"type": "integer"},
            "duration_seconds": {"type": "integer", "default": 10},
            "lore_book": {"type": "string"},
            "history_limit": {"type": "integer", "default": 20},
            "tts_voice": {"type": "string", "default": "hakua"},
            "tts_model": {"type": "string", "default": "irodori-tts"},
            "tts_speed": {"type": "number", "default": 1.0},
            "stt_model": {"type": "string", "default": "base"},
            "auto_memory": {"type": "boolean", "default": True},
        }, "required": ["session_id"]},
        handler=st_voice_roleplay,
    )
    ctx.register_tool(
        name="st_voice_roleplay_complete",
        toolset="sillytavern",
        description="Voice roleplay turn (phase 2): record assistant reply -> TTS (irodori/hakua) -> play -> memory bridge.",
        schema={"type": "object", "properties": {
            "session_id": {"type": "integer"},
            "reply_content": {"type": "string"},
            "tts_voice": {"type": "string", "default": "hakua"},
            "tts_model": {"type": "string", "default": "irodori-tts"},
            "tts_speed": {"type": "number", "default": 1.0},
            "auto_memory": {"type": "boolean", "default": True},
        }, "required": ["session_id", "reply_content"]},
        handler=st_voice_roleplay_complete,
    )
    # ── Audio landing: copy audio/zip from irodori buffer into ST uploads ──
    ctx.register_tool(
        name="st_audio_land",
        toolset="sillytavern",
        description="Copy the latest audio file or zip from the irodori audio buffer into SillyTavern's data/_uploads/ directory.",
        schema={
            "type": "object",
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "Optional absolute path to an audio file or zip. Omit to use the latest from the irodori buffer.",
                },
                "target_name": {
                    "type": "string",
                    "description": "Optional filename under _uploads/. Defaults to the source basename.",
                },
            },
        },
        handler=sillytavern_audio_land,
        check_fn=_installed,
    )

    # Slash + terminal CLI stay in the plugin (no core cli.py / COMMAND_REGISTRY).
    from .cli import register_cli, sillytavern_command
    from .slash import handle_rp, handle_st_voice_roleplay

    ctx.register_command(
        "rp",
        handler=handle_rp,
        description="ST-native roleplay quick ops (list/create/start/say/reply/summary/memory/lore).",
        args_hint="[list|create|start|say|reply|summary|memory|lore|status|help]",
    )
    ctx.register_command(
        "st-voice-roleplay",
        handler=handle_st_voice_roleplay,
        description="Voice roleplay turn helpers (STT → ST-native → TTS).",
        args_hint="[start|complete|status] <session_id> [args...]",
    )
    ctx.register_cli_command(
        name="sillytavern",
        help="Manage local SillyTavern and ST-native roleplay helpers",
        setup_fn=register_cli,
        handler_fn=sillytavern_command,
        description=(
            "Start/stop/status for the pinned SillyTavern server, generate via its "
            "API, and run ST-native / voice roleplay quick ops without core CLI wiring."
        ),
    )
