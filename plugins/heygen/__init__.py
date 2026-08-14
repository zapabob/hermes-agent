"""HeyGen CLI binary wrapper plugin for Hermes Agent."""

import os
import shutil
import subprocess
import json
from pathlib import Path

from hermes_constants import get_hermes_home

PLUGIN_DIR = Path(__file__).resolve().parent
VENDOR_DIR = PLUGIN_DIR.parent.parent / "vendor" / "heygen-cli"
BINARY = VENDOR_DIR / "bin" / "heygen.exe"


def _resolve_binary(user_cfg=None):
    """Resolve heygen binary path: config → vendor → PATH."""
    cfg_path = (user_cfg or {}).get("binary_path", "")
    if cfg_path and Path(cfg_path).exists():
        return str(Path(cfg_path).resolve())
    if BINARY.exists():
        return str(BINARY)
    path_bin = shutil.which("heygen") or shutil.which("heygen.exe")
    if path_bin:
        return path_bin
    return ""


def _run(args, timeout=120, env=None):
    """Run heygen CLI and return (exit_code, stdout, stderr)."""
    bin_path = _resolve_binary()
    if not bin_path:
        return 1, "", "heygen binary not found"
    cmd = [bin_path] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            env=env or os.environ.copy()
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 4, "", "timeout"
    except Exception as e:
        return 1, "", str(e)


def heygen_status(args, **kw):
    """Check HeyGen CLI installation and auth status."""
    task_id = kw.get("task_id")
    bin_path = _resolve_binary()
    if not bin_path:
        return json.dumps({"ok": False, "error": "Binary not found", "path": ""})

    rc, out, err = _run(["--version"], timeout=10)
    if rc != 0:
        return json.dumps({"ok": False, "error": err, "path": bin_path})

    auth_rc, auth_out, auth_err = _run(["auth", "status"], timeout=15)
    return json.dumps({
        "ok": True,
        "path": bin_path,
        "version": out,
        "auth": auth_out if auth_rc == 0 else auth_err,
        "authed": auth_rc == 0
    })


def heygen_video_create(args, **kw):
    """Create a video from a text prompt.

    Args:
        prompt: Text prompt for the video
        wait: bool = True — block until video is ready
        timeout: int = 1200 — max wait seconds
    """
    task_id = kw.get("task_id")
    prompt = args.get("prompt", "")
    wait = args.get("wait", True)
    timeout = int(args.get("timeout", 1200))

    if not prompt:
        return json.dumps({"ok": False, "error": "prompt required"})

    cmd = ["video-agent", "create", "--prompt", prompt]
    if wait:
        cmd += ["--wait", "--timeout", str(timeout)]

    rc, out, err = _run(cmd, timeout=timeout + 30)

    if rc == 0:
        try:
            data = json.loads(out)
            return json.dumps({"ok": True, "data": data, "task_id": task_id})
        except json.JSONDecodeError:
            return json.dumps({"ok": True, "raw": out, "task_id": task_id})
    return json.dumps({"ok": False, "error": err or out, "code": rc})


def heygen_video_get(args, **kw):
    """Get video metadata by ID.

    Args:
        video_id: str — HeyGen video ID
    """
    task_id = kw.get("task_id")
    video_id = args.get("video_id", "")
    if not video_id:
        return json.dumps({"ok": False, "error": "video_id required"})

    rc, out, err = _run(["video", "get", video_id], timeout=30)
    if rc == 0:
        try:
            data = json.loads(out)
            return json.dumps({"ok": True, "data": data, "task_id": task_id})
        except json.JSONDecodeError:
            return json.dumps({"ok": True, "raw": out, "task_id": task_id})
    return json.dumps({"ok": False, "error": err or out, "code": rc})


def heygen_video_download(args, **kw):
    """Download video MP4 to local file.

    Args:
        video_id: str — HeyGen video ID
        output_path: str = "" — destination path (optional)
    """
    task_id = kw.get("task_id")
    video_id = args.get("video_id", "")
    output_path = args.get("output_path", "")

    if not video_id:
        return json.dumps({"ok": False, "error": "video_id required"})

    cmd = ["video", "download", video_id]
    if output_path:
        cmd += ["--output", output_path]

    rc, out, err = _run(cmd, timeout=120)
    if rc == 0:
        try:
            data = json.loads(out)
            return json.dumps({"ok": True, "path": data.get("path", ""), "data": data, "task_id": task_id})
        except json.JSONDecodeError:
            return json.dumps({"ok": True, "raw": out, "task_id": task_id})
    return json.dumps({"ok": False, "error": err or out, "code": rc})


def heygen_auth_status(args, **kw):
    """Check HeyGen authentication status."""
    task_id = kw.get("task_id")
    rc, out, err = _run(["auth", "status"], timeout=15)
    if rc == 0:
        return json.dumps({"ok": True, "status": out, "authed": True, "task_id": task_id})
    return json.dumps({"ok": False, "error": err or out, "authed": False, "code": rc})


def _installed():
    """Check if heygen binary is available."""
    return bool(_resolve_binary())


def register(ctx):
    ctx.register_tool(
        name="heygen_status",
        toolset="heygen",
        description="Check HeyGen CLI installation and auth status.",
        schema={
            "type": "object",
            "properties": {},
        },
        handler=heygen_status,
        check_fn=_installed,
    )

    ctx.register_tool(
        name="heygen_auth_status",
        toolset="heygen",
        description="Check HeyGen API authentication status.",
        schema={
            "type": "object",
            "properties": {},
        },
        handler=heygen_auth_status,
        check_fn=_installed,
    )

    ctx.register_tool(
        name="heygen_video_create",
        toolset="heygen",
        description="Create a video from a text prompt using HeyGen AI.",
        schema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Text prompt for the video content."},
                "wait": {"type": "boolean", "default": True, "description": "Block until video is ready."},
                "timeout": {"type": "integer", "default": 1200, "description": "Max wait seconds."},
            },
            "required": ["prompt"],
        },
        handler=heygen_video_create,
        check_fn=_installed,
        requires_env=["HEYGEN_API_KEY"],
    )

    ctx.register_tool(
        name="heygen_video_get",
        toolset="heygen",
        description="Get video metadata by HeyGen video ID.",
        schema={
            "type": "object",
            "properties": {
                "video_id": {"type": "string", "description": "HeyGen video ID."},
            },
            "required": ["video_id"],
        },
        handler=heygen_video_get,
        check_fn=_installed,
    )

    ctx.register_tool(
        name="heygen_video_download",
        toolset="heygen",
        description="Download a HeyGen video as MP4.",
        schema={
            "type": "object",
            "properties": {
                "video_id": {"type": "string", "description": "HeyGen video ID."},
                "output_path": {"type": "string", "description": "Local file path to save the MP4 (optional)."},
            },
            "required": ["video_id"],
        },
        handler=heygen_video_download,
        check_fn=_installed,
    )
