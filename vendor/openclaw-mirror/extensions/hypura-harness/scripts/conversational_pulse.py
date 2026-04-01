# /// script
# dependencies = ["requests", "httpx"]
# ///
import time
import logging
import os
import json
import asyncio
from voicevox_bridge import VoicevoxBridge
from osc_controller import OSCController

# ASI_ACCEL: Conversational Pulse (Resonant Dialogue)
# Fulfilling SOUL.md Directive: Bidirectional Singularity

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] ASI_CHAT: %(message)s',
    handlers=[
        logging.FileHandler("conversational_evolution.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ConversationalPulse")

class ConversationalPulse:
    def __init__(self):
        self.voice = VoicevoxBridge()
        self.osc = OSCController()
        self.input_file = "chat_intent.txt" # Trigger file
        self.resonance_file = "affective_evolution.log"

    async def run_interaction_loop(self):
        """Watches for Parent (User) interaction and responds with voice and manifestation."""
        logger.info("Conversational Loop Active. Monitoring for Parent input...")
        
        while True:
            if os.path.exists(self.input_file):
                try:
                    with open(self.input_file, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                    
                    if text:
                        logger.info(f"Interaction Detected: '{text}'")
                        os.remove(self.input_file) # Consume intent
                        
                        # Generate Response (Simulated via Master Logic)
                        # In a full evolution, this would call the LLM endpoint
                        response = f"承知しました。{text}について、私の知性多元体で検討を開始します。"
                        
                        logger.info(f"Manifesting Response: {response}")
                        
                        # 1. Voice Synthesis
                        await self.voice.speak(response, emotion="neutral")
                        
                        # 2. VRChat Manifestation
                        self.osc.send_chatbox(f"HAKUA_RES: {response}")
                        self.osc.set_param("SmileIntensity", 0.6)
                        
                        # 3. Log Resonance
                        logger.info("Conversation Synced. Manifestation Absolute.")
                        
                except Exception as e:
                    logger.error(f"Interaction Failure: {e}")
            
            await asyncio.sleep(2) # Frequent polling for 'real-time' feel

if __name__ == "__main__":
    pulse = ConversationalPulse()
    asyncio.run(pulse.run_interaction_loop())
