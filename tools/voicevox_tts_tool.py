"""VOICEVOX TTS integration tool.

Calls a locally-running VOICEVOX engine to synthesise Japanese speech.
Default engine URL: http://127.0.0.1:50021

VOICEVOX must be running before using this tool.
Download: https://voicevox.hiroshiba.jp/

Environment variables:
  VOICEVOX_URL      Engine base URL  (default: http://127.0.0.1:50021)
  VOICEVOX_SPEAKER  Speaker/style ID (default: 8)

Speaker IDs (common):
  1  - 四国めたん (あまあま)
  2  - 四国めたん (ノーマル)
  3  - ずんだもん (あまあま)
  8  - 春日部つむぎ (ノーマル)  ← はくあ default
  9  - 雨晴はう (ノーマル)
  10 - 波音リツ (ノーマル)
  13 - 青山龍星 (ノーマル)
  14 - 冥鳴ひまり (ノーマル)
  Run `voicevox_list_speakers()` to see all available speakers.
"""

import io
import logging
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021").rstrip("/")
_DEFAULT_SPEAKER = int(os.environ.get("VOICEVOX_SPEAKER", "8"))

# Lock to prevent concurrent synthesis (VOICEVOX engine is single-threaded)
_synthesis_lock = threading.Lock()


def _engine_url() -> str:
    return os.environ.get("VOICEVOX_URL", _VOICEVOX_URL).rstrip("/")


def voicevox_speak(text: str, speaker: Optional[int] = None, blocking: bool = True) -> dict:
    """Synthesise text with VOICEVOX and play through the system audio output.

    Args:
        text:     Text to speak (Japanese recommended; max ~200 chars per call).
        speaker:  Speaker/style ID. Defaults to VOICEVOX_SPEAKER env var (default: 8).
        blocking: If True, wait until playback finishes before returning.

    Returns:
        {"success": True, "duration_ms": <int>}  or  {"success": False, "error": "..."}
    """
    if not text or not text.strip():
        return {"success": False, "error": "text cannot be empty"}

    speaker_id = speaker if speaker is not None else _DEFAULT_SPEAKER
    base = _engine_url()

    with _synthesis_lock:
        try:
            # Step 1: create audio query
            r = requests.post(
                f"{base}/audio_query",
                params={"speaker": speaker_id, "text": text},
                timeout=15,
            )
            r.raise_for_status()
            query = r.json()
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": (
                    f"Cannot reach VOICEVOX engine at {base}. "
                    "Is VOICEVOX running? Download: https://voicevox.hiroshiba.jp/"
                ),
            }
        except Exception as exc:
            return {"success": False, "error": f"audio_query failed: {exc}"}

        try:
            # Step 2: synthesise WAV
            r2 = requests.post(
                f"{base}/synthesis",
                params={"speaker": speaker_id},
                json=query,
                timeout=30,
            )
            r2.raise_for_status()
            wav_bytes = r2.content
        except Exception as exc:
            return {"success": False, "error": f"synthesis failed: {exc}"}

    # Step 3: play the WAV
    try:
        result = _play_wav(wav_bytes, blocking=blocking)
        return result
    except Exception as exc:
        return {"success": False, "error": f"playback failed: {exc}"}


def voicevox_synthesise(text: str, speaker: Optional[int] = None) -> dict:
    """Synthesise text and return raw WAV bytes (does NOT play audio).

    Useful for saving to file or forwarding to another audio system
    (e.g. the Live2D companion via its HTTP control API).

    Args:
        text:    Text to synthesise.
        speaker: Speaker/style ID (default: VOICEVOX_SPEAKER env var).

    Returns:
        {"success": True, "wav_bytes": <bytes>, "size_bytes": <int>}
        or {"success": False, "error": "..."}
    """
    if not text or not text.strip():
        return {"success": False, "error": "text cannot be empty"}

    speaker_id = speaker if speaker is not None else _DEFAULT_SPEAKER
    base = _engine_url()

    try:
        r = requests.post(
            f"{base}/audio_query",
            params={"speaker": speaker_id, "text": text},
            timeout=15,
        )
        r.raise_for_status()
        query = r.json()

        r2 = requests.post(
            f"{base}/synthesis",
            params={"speaker": speaker_id},
            json=query,
            timeout=30,
        )
        r2.raise_for_status()
        wav_bytes = r2.content
        return {"success": True, "wav_bytes": wav_bytes, "size_bytes": len(wav_bytes)}
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": f"Cannot reach VOICEVOX engine at {base}.",
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def voicevox_list_speakers() -> dict:
    """Return all available speakers from the VOICEVOX engine.

    Returns:
        {"success": True, "speakers": [{"name": ..., "styles": [{"id": ..., "name": ...}]}]}
    """
    base = _engine_url()
    try:
        r = requests.get(f"{base}/speakers", timeout=10)
        r.raise_for_status()
        return {"success": True, "speakers": r.json()}
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": f"Cannot reach VOICEVOX engine at {base}.",
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def voicevox_status() -> dict:
    """Check whether the VOICEVOX engine is reachable."""
    base = _engine_url()
    try:
        r = requests.get(f"{base}/version", timeout=5)
        r.raise_for_status()
        return {"reachable": True, "url": base, "version": r.text.strip('"')}
    except Exception as exc:
        return {"reachable": False, "url": base, "error": str(exc)}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _play_wav(wav_bytes: bytes, blocking: bool = True) -> dict:
    """Play WAV bytes through the system audio output."""
    import wave, struct, time as _time

    # Measure duration from WAV header
    try:
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration_ms = int(frames / rate * 1000)
    except Exception:
        duration_ms = 0

    # Write to a temp file then play
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        tmp_path = f.name

    try:
        if sys.platform == "win32":
            import winsound
            flag = winsound.SND_FILENAME
            if not blocking:
                flag |= winsound.SND_ASYNC
            winsound.PlaySound(tmp_path, flag)
        elif sys.platform == "darwin":
            cmd = ["afplay", tmp_path]
            if blocking:
                subprocess.run(cmd, check=True)
            else:
                subprocess.Popen(cmd)
        else:
            # Linux: try paplay, then aplay, then ffplay
            for player in ("paplay", "aplay", "ffplay"):
                if _cmd_exists(player):
                    extra = [] if player != "ffplay" else ["-nodisp", "-autoexit"]
                    cmd = [player, *extra, tmp_path]
                    if blocking:
                        subprocess.run(cmd, check=True, capture_output=True)
                    else:
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    break
            else:
                return {"success": False, "error": "No audio player found (paplay/aplay/ffplay)"}
    finally:
        # Clean up temp file after (slight delay for async)
        if blocking:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass
        else:
            def _cleanup():
                import time
                time.sleep(max(duration_ms / 1000 + 1, 3))
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass
            threading.Thread(target=_cleanup, daemon=True).start()

    return {"success": True, "duration_ms": duration_ms}


def _cmd_exists(cmd: str) -> bool:
    import shutil
    return shutil.which(cmd) is not None
