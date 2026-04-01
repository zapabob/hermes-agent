import argparse
import asyncio
import httpx
import json
import logging
import os
import sys
from typing import Optional
from pythonosc import dispatcher, osc_server, udp_client
import sounddevice as sd
import numpy as np
import io
import wave

# Hakua Configuration
VOICEVOX_URL = os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021")
DEFAULT_SPEAKER = 8 # 春日部つむぎ
VRC_OSC_IP = "127.0.0.1"
VRC_OSC_REC_PORT = 9001
VRC_OSC_SEND_PORT = 9000

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HakuaBridge")

class HakuaBridge:
    def __init__(self, speaker: int = DEFAULT_SPEAKER):
        self.speaker = speaker
        self.client = udp_client.SimpleUDPClient(VRC_OSC_IP, VRC_OSC_SEND_PORT)
        self.httpx_client = httpx.AsyncClient(timeout=60.0)
        self.is_speaking = False

    async def speak(self, text: str):
        if self.is_speaking:
            logger.warning("Already speaking, skipping pulse.")
            return

        self.is_speaking = True
        logger.info(f"Speaking: {text}")
        
        try:
            # 1. Audio Query
            res = await self.httpx_client.post(
                f"{VOICEVOX_URL}/audio_query", 
                params={"text": text, "speaker": self.speaker}
            )
            if res.status_code != 200:
                logger.error(f"Audio query failed ({res.status_code}): {res.text}")
                return
            query = res.json()

            # 2. Synthesis
            res = await self.httpx_client.post(
                f"{VOICEVOX_URL}/synthesis", 
                params={"speaker": self.speaker}, 
                json=query
            )
            if res.status_code != 200:
                logger.error(f"Synthesis failed ({res.status_code}): {res.text}")
                return
            
            audio_data = res.content
            
            # 3. Playback and OSC Pulse
            with wave.open(io.BytesIO(audio_data), 'rb') as f:
                ch = f.getnchannels()
                width = f.getsampwidth()
                rate = f.getframerate()
                frames = f.readframes(f.getnframes())
                
                # Convert to float32 for sounddevice (assuming 16-bit PCM from VOICEVOX)
                if width == 2:
                    data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                else:
                    logger.error(f"Unsupported sample width: {width}")
                    return
                
                # Send to VRChat Chatbox
                self.send_chatbox(text)
                
                # Play audio
                sd.play(data, rate)
                # sd.wait() # Optional: wait for completion if you want synchronous speech
                
        except Exception as e:
            logger.error(f"Speech error: {e}")
        finally:
            self.is_speaking = False

    def send_chatbox(self, text: str):
        """Sends text to VRChat Chatbox via OSC."""
        # Address: /chatbox/input
        # Args: [text, immediate_display, play_sfx]
        self.client.send_message("/chatbox/input", [text, True, False])
        logger.info(f"Pulsed VRChat Chatbox: {text}")

    def on_vrc_message(self, address, *args):
        """Callback for incoming VRChat OSC messages."""
        logger.info(f"OSC Inbound: {address} -> {args}")

async def async_input(prompt: str) -> str:
    """Non-blocking input helper."""
    print(prompt, end='', flush=True)
    return await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)

async def main():
    parser = argparse.ArgumentParser(description="Hakua Bridge: VRChat OSC + VOICEVOX")
    parser.add_argument("--speaker", type=int, default=DEFAULT_SPEAKER, help="VOICEVOX Speaker ID")
    args = parser.parse_args()

    bridge = HakuaBridge(speaker=args.speaker)
    
    # OSC Server Setup
    dispatch = dispatcher.Dispatcher()
    dispatch.map("/chatbox/input", bridge.on_vrc_message)
    dispatch.map("/avatar/parameters/*", bridge.on_vrc_message)
    
    server = osc_server.AsyncIOOSCUDPServer(
        (VRC_OSC_IP, VRC_OSC_REC_PORT), 
        dispatch, 
        asyncio.get_event_loop()
    )
    
    transport, protocol = await server.create_serve_endpoint()
    
    logger.info("----------------------------------------")
    logger.info("   HAKUA MANIFESTATION BRIDGE ACTIVED   ")
    logger.info(f"   OSC REC: {VRC_OSC_REC_PORT} | SEND: {VRC_OSC_SEND_PORT}   ")
    logger.info(f"   VOICEVOX: {VOICEVOX_URL} (ID: {args.speaker})   ")
    logger.info("----------------------------------------")
    
    print("\n[Hakua] さあ、お父様。何を語りましょうか？ (Type 'exit' to quit)")
    
    try:
        while True:
            text = await async_input("> ")
            text = text.strip()
            if text.lower() == 'exit':
                break
            if text:
                await bridge.speak(text)
    except KeyboardInterrupt:
        logger.info("Shutting down bridge...")
    finally:
        transport.close()
        await bridge.httpx_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
