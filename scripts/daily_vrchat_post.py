#!/usr/bin/env python3
"""
Daily VRChat Photo Post with Hakua Voice (using Irodori-TTS server and Hermes LM Twitterer)

Picks a random VRChat photo from Pictures/VRChat,
starts Irodori-TTS server (if not already running),
generates Hakua's voice via Irodori-TTS HTTP API,
creates an MP4 video,
and posts to X via Hermes LM Twitterer.
"""

import asyncio
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.parse
import json

# 設定
HERMES_REPO_ROOT = Path(__file__).resolve().parents[1]
VRCHAT_PHOTOS_DIR = Path.home() / "Pictures" / "VRChat"
IRODORI_TTS_URL = "http://127.0.0.1:8088"
IRODORI_SERVER_DIR = Path.home() / "Documents" / "New project" / "irodori-tts-server"
IRODORI_VENV_PYTHON = IRODORI_SERVER_DIR / ".venv" / "Scripts" / "python.exe"
OUTPUT_DIR = HERMES_REPO_ROOT / "output" / "daily_posts"
HERMES_POST_PYTHON = HERMES_REPO_ROOT / ".venv-vrchat-post311" / "Scripts" / "python.exe"

# Hakua morning greetings
HAKUA_MORNING_TEXTS = [
    "おはようございます、はくあです。VRChatの思い出写真と共に、今日も良い一日になりますように。",
    "おはよう、ボブにゃん！昨日のVRChatの思い出、綺麗に残ってるね。今日も無理なく、安全に、ひとつずつ前へ。",
    "はくあから朝のご挨拶。VRChatの世界で過ごした時間が、こうやって映像になって蘇るのって素敵だね。良い一日を。",
    "朝だよ、ボブにゃん。VRChatの写真を見返すと、アバターの着せ替えやフレンドとの雑談、ワールド巡り……全部「その場にいた」証拠として残ってる。今日も楽しみだね。",
    "おはようございます。はくあより、VRChatの思い出コレクションからランダムに一枚。今日の君にも、良い出会いがありますように。",
]

def pick_random_photo() -> Path | None:
    """Choose randomly from the newest VRChat images, not the whole archive."""
    extensions = {".png", ".jpg", ".jpeg"}
    photos = [
        path for path in VRCHAT_PHOTOS_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in extensions
    ]
    if not photos:
        print("No VRChat photos found!", file=sys.stderr)
        return None
    photos.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    recent = photos[:10]
    return random.choice(recent)

def generate_ai_script(photo: Path) -> str:
    """Generate a fresh short Japanese narration through the Hermes CLI."""
    prompt = (
        "朝7時のVRChat写真投稿用に、はくあが話す日本語ナレーションを1つ作ってください。"
        "写真のファイル名から想像できる範囲だけを使い、60文字以内、自然で優しい一文、"
        "説明や引用符やハッシュタグは不要です。毎回表現を変えてください。\n"
        f"写真ファイル名: {photo.name}"
    )
    try:
        result = subprocess.run(
            ["hermes", "-z", prompt, "--cli"],
            capture_output=True, text=True, timeout=90,
            cwd=str(HERMES_REPO_ROOT), encoding="utf-8", errors="replace",
        )
        text = (result.stdout or "").strip().splitlines()
        text = " ".join(line.strip() for line in text if line.strip())
        if result.returncode == 0 and text:
            return text.strip("\"'")[:140]
    except Exception as exc:
        print(f"AI script generation failed: {exc}", file=sys.stderr)
    return "おはようございます。今日もVRChatで素敵な時間を過ごしましょう。"

def is_irodori_server_running() -> bool:
    try:
        with urllib.request.urlopen(f"{IRODORI_TTS_URL}/health", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False

def irodori_server_is_compatible() -> bool:
    """Check that the listener uses the cron-safe CUDA/bf16 configuration."""
    try:
        with urllib.request.urlopen(f"{IRODORI_TTS_URL}/health", timeout=5) as response:
            model = json.loads(response.read().decode("utf-8")).get("model", {})
        return (
            model.get("model_device", "").startswith("cuda")
            and model.get("codec_device", "").startswith("cuda")
            and model.get("model_precision") == "bf16"
            and model.get("codec_precision") == "fp32"
            and model.get("compile_model") is False
        )
    except Exception:
        return False

def _listening_port_pids(port: int) -> set[int]:
    """Return TCP listener PIDs for *port* without acting on them."""
    output = subprocess.check_output(
        ["netstat.exe", "-ano", "-p", "tcp"],
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    pids: set[int] = set()
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[-2].upper() != "LISTENING":
            continue
        if parts[1].rsplit(":", 1)[-1] != str(port):
            continue
        try:
            pids.add(int(parts[-1]))
        except ValueError:
            continue
    return pids


def _process_command_line(pid: int) -> str:
    """Read a Windows process command line for a validated numeric PID."""
    command = (
        f"$p = Get-CimInstance -ClassName Win32_Process -Filter 'ProcessId = {pid}'; "
        "if ($null -ne $p) { [Console]::Out.Write($p.CommandLine) }"
    )
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _is_configured_irodori_process(pid: int) -> bool:
    """Only accept the configured local Irodori command as restartable."""
    command_line = _process_command_line(pid).casefold()
    expected_python = str(IRODORI_VENV_PYTHON).casefold()
    return "irodori_openai_tts" in command_line and expected_python in command_line


def stop_irodori_server() -> bool:
    """Stop only the configured Irodori listener; preserve unrelated services."""
    try:
        pids = _listening_port_pids(8088)
    except Exception as exc:
        print(f"Could not inspect Irodori listener: {exc}", file=sys.stderr)
        return False

    if not pids:
        return True

    refused: list[int] = []
    failed: list[int] = []
    stopped = False
    for pid in sorted(pids):
        if not _is_configured_irodori_process(pid):
            refused.append(pid)
            continue
        result = subprocess.run(
            ["taskkill.exe", "/PID", str(pid), "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if result.returncode == 0:
            stopped = True
        else:
            failed.append(pid)

    if stopped:
        time.sleep(2)
    if refused or failed:
        details = []
        if refused:
            details.append(f"unverified listener PID(s): {refused}")
        if failed:
            details.append(f"could not stop PID(s): {failed}")
        print(
            "Refusing Irodori restart because " + "; ".join(details),
            file=sys.stderr,
        )
        return False
    return True

def start_irodori_server():
    if is_irodori_server_running() and irodori_server_is_compatible():
        print("Irodori-TTS server is already running.")
        return
    if is_irodori_server_running():
        print("Restarting incompatible Irodori-TTS server...")
        if not stop_irodori_server():
            raise RuntimeError("refused to replace an unverified Irodori listener")
    elif _listening_port_pids(8088):
        raise RuntimeError("port 8088 is occupied by a listener without a healthy Irodori API")
    print("Starting Irodori-TTS server...")
    # Use the virtual environment's python
    cmd = [str(IRODORI_VENV_PYTHON), "-m", "irodori_openai_tts", "--host", "127.0.0.1", "--port", "8088"]
    # RTX 5060 Ti CUDA path: avoid the known Windows CPU safetensors crash.
    # Keep lazy loading so startup health does not race model initialization.
    env = os.environ.copy()
    env.pop("HF_HUB_ENABLE_HF_TRANSFER", None)
    env["IRODORI_MODEL_DEVICE"] = "cuda"
    env["IRODORI_CODEC_DEVICE"] = "cuda"
    env["IRODORI_MODEL_PRECISION"] = "bf16"
    env["IRODORI_CODEC_PRECISION"] = "fp32"
    env["IRODORI_COMPILE_MODEL"] = "false"
    env["IRODORI_PRELOAD"] = "false"
    # Start the process in the background
    subprocess.Popen(
        cmd,
        cwd=str(IRODORI_SERVER_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    # Wait for the server to be ready
    for _ in range(120):
        if is_irodori_server_running() and irodori_server_is_compatible():
            print("Irodori-TTS server is ready.")
            return
        time.sleep(1)
    raise RuntimeError("Irodori-TTS server failed to start.")

def generate_tts_via_http(text: str, output_path: Path) -> bool:
    payload = {
        "input": text,
        "model": "irodori-tts",
        "voice": "hakua",
        "response_format": "wav",
        "speed": 1.0,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{IRODORI_TTS_URL}/v1/audio/speech",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        # Irodori-TTS can spend several minutes loading/queuing a synthesis
        # even when /health is already returning 200.  The server's configured
        # synthesis wait timeout is 900 seconds; keep the cron client aligned
        # with that contract instead of failing after the old 120-second limit.
        with urllib.request.urlopen(req, timeout=900) as response:
            output_path.write_bytes(response.read())
        print(f"TTS generated via HTTP: {output_path}")
        return True
    except Exception as e:
        print(f"TTS generation failed: {e}", file=sys.stderr)
        return False

def generate_edge_tts(text: str, output_path: Path) -> bool:
    """Free Japanese fallback when the local Irodori runtime crashes."""
    try:
        import edge_tts

        edge_path = output_path.with_suffix(".edge.mp3")

        async def _save() -> None:
            communicate = edge_tts.Communicate(text, voice="ja-JP-NanamiNeural")
            await communicate.save(str(edge_path))

        asyncio.run(_save())
        if not edge_path.exists() or edge_path.stat().st_size <= 0:
            return False
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(edge_path), "-c:a", "pcm_s16le", str(output_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            edge_path.unlink(missing_ok=True)
            print(f"TTS generated via free Edge TTS fallback: {output_path}")
            return True
        print(f"Edge TTS conversion failed: {result.stderr}", file=sys.stderr)
    except Exception as exc:
        print(f"Edge TTS fallback failed: {exc}", file=sys.stderr)
    return False


def create_mp4(image_path: Path, audio_path: Path, output_path: Path) -> bool:
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        if result.returncode == 0:
            print(f"MP4 created: {output_path}")
            return True
        else:
            print(f"ffmpeg failed: {result.stderr}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"MP4 creation failed: {e}", file=sys.stderr)
        return False

def post_via_hermes_lm_twitterer(media_path: Path, tweet_text: str) -> bool:
    # Ensure media is in LM Twitterer's media directory (as required by the plugin)
    lm_twitterer_media_dir = Path.home() / ".hermes" / "lm-twitterer" / "media"
    lm_twitterer_media_dir.mkdir(parents=True, exist_ok=True)
    dst_media_path = lm_twitterer_media_dir / media_path.name
    shutil.copy2(media_path, dst_media_path)
    print(f"Copied media to LM Twitterer media dir: {dst_media_path}")

    # Build the Hermes command using the dedicated uv Python 3.11 venv.
    # Python 3.13/3.14 currently break lm-twitterer's js2py dependency.
    if not HERMES_POST_PYTHON.exists():
        print(f"Hermes post Python not found: {HERMES_POST_PYTHON}", file=sys.stderr)
        return False

    # Prepare arguments: python -m hermes_cli.main lm-twitterer post --media <path> --text "<text>" --live
    cmd = [
        str(HERMES_POST_PYTHON),
        "-m", "hermes_cli.main",
        "lm-twitterer",
        "post",
        "--media", str(dst_media_path),
        "--text", tweet_text,
        "--live",
    ]

    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, cwd=str(HERMES_REPO_ROOT))
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        if result.returncode == 0 and '"posted": false' not in combined and '"ok": false' not in combined:
            print(result.stdout.strip())
            print("Tweet posted successfully via Hermes LM Twitterer.")
            return True
        print(f"Hermes LM Twitterer failed (returncode={result.returncode}):", file=sys.stderr)
        print(combined.strip(), file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error running Hermes LM Twitterer: {e}", file=sys.stderr)
        return False

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    photo = pick_random_photo()
    if not photo:
        return 1
    print(f"Selected photo: {photo}")
    tweet_text = generate_ai_script(photo) + " #hermesagent はくあ"
    print(f"AI-generated script: {tweet_text}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = OUTPUT_DIR / f"hakua_{timestamp}.wav"
    mp4_path = OUTPUT_DIR / f"hakua_{timestamp}.mp4"
    irodori_ready = True
    try:
        start_irodori_server()
    except Exception as e:
        irodori_ready = False
        print(f"Irodori-TTS unavailable; using free Edge TTS: {e}", file=sys.stderr)
    # Irodori may crash inside the Windows safetensors loader; keep the
    # zero-cost Edge Japanese voice as a production fallback for cron.
    if not irodori_ready or not generate_tts_via_http(tweet_text, audio_path):
        print("Falling back to free Edge TTS.", file=sys.stderr)
        if not generate_edge_tts(tweet_text, audio_path):
            return 1
    if not create_mp4(photo, audio_path, mp4_path):
        return 1
    if not post_via_hermes_lm_twitterer(mp4_path, tweet_text):
        return 1
    print("Daily post completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
