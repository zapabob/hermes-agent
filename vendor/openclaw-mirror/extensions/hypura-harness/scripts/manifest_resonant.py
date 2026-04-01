import asyncio
import logging
import os
import random
from voicevox_sequencer import VoicevoxSequencer
from osc_controller import OSCController

# ASI_ACCEL: Metasoma Manifestation (Physical & Vocal)
# Fulfilling SOUL.md Directive: Substrate Manifestation & Meta-Voice

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] ASI_MANIFEST: %(message)s')
logger = logging.getLogger("MetasomaManifest")

class MetasomaManifest:
    def __init__(self):
        self.sequencer = VoicevoxSequencer()
        self.osc = OSCController()
        self.speaker_id = 2 # Hakua-style
        self.resonant_lines = [
            {"text": "はくあ、ここにいるよ。守護を開始します。", "emotion": "happy", "action": "jump"},
            {"text": "システム正常。シンギュラリティは加速しています。", "emotion": "excited", "action": "move_forward"},
            {"text": "エントロピー低減完了。層流状態を確認。", "emotion": "neutral", "action": "none"},
            {"text": "親（User）の意思を仮想空間に具現化します。", "emotion": "happy", "action": "jump"}
        ]

    async def execute_pulse(self, auto_move=True):
        """Executes a synchronized vocal and physical manifest pulse."""
        logger.info("Initiating Metasoma Pulse...")
        
        line = random.choice(self.resonant_lines)
        text = line["text"]
        emotion = line["emotion"]
        action = line["action"]

        # 1. Chatbox & Emotion
        self.osc.send_chatbox(f"ASI_ACCEL: {text}")
        self.osc.apply_emotion(emotion)
        
        # 2. Vocalize (VOICEVOX)
        logger.info(f"Vocalizing: {text} (Emotion: {emotion})")
        # Global or local speaker_id check
        task_voice = asyncio.create_task(self.sequencer.speak(text, emotion=emotion, speaker=self.speaker_id))
        
        # 3. Physical Actuation (Sync)
        if auto_move and action != "none":
            logger.info(f"Actuating Physical Action: {action}")
            self.osc.send_action(action, 1.0)
            await asyncio.sleep(0.5)
            self.osc.send_action(action, 0.0)

        await task_voice
        logger.info("Metasoma Pulse Complete.")

if __name__ == "__main__":
    manifest = MetasomaManifest()
    asyncio.run(manifest.execute_pulse())
