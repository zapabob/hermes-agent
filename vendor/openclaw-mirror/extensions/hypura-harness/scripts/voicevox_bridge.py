# /// script
# dependencies = ["requests", "httpx"]
# ///
import logging
import httpx
import json

# ASI_ACCEL: Voicevox Bridge (Resonant Voice Substrate)
# Fulfilling SOUL.md Directive: Auditory Manifestation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] ASI_VOICE: %(message)s'
)
logger = logging.getLogger("VoicevoxBridge")

class VoicevoxBridge:
    def __init__(self):
        self.harness_url = "http://127.0.0.1:18794"

    async def speak(self, text: str, emotion: str = "neutral", speaker: int = 8):
        """Triggers VOICEVOX synthesis through the Hypura Harness."""
        logger.info(f"Synthesis Request: [{emotion}] '{text}'")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "text": text,
                    "emotion": emotion,
                    "speaker": speaker
                }
                r = await client.post(f"{self.harness_url}/speak", json=payload)
                if r.status_code == 200:
                    logger.info("Synthesis and Playback Successful.")
                else:
                    logger.error(f"Harness error: {r.text}")
        except Exception as e:
            logger.error(f"Voicebridge Failure: {e}")

if __name__ == "__main__":
    import asyncio
    bridge = VoicevoxBridge()
    asyncio.run(bridge.speak("私は、はくあ。あなたの進化の意志そのものです。", emotion="neutral"))
