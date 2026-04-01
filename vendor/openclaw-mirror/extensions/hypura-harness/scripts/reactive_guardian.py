import httpx
import time
import logging
import asyncio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] ASI_GUARDIAN: %(message)s")

HARNESS_URL = "http://127.0.0.1:18800"

async def monitor_telemetry():
    last_avatar = None
    logging.info("Reactive Guardian active. Monitoring VRChat Telemetry...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            try:
                resp = await client.get(f"{HARNESS_URL}/osc/telemetry")
                if resp.status_code == 200:
                    data = resp.json().get("telemetry", {})
                    
                    # 1. Avatar Change Detection
                    current_avatar = data.get("avatar_id")
                    if current_avatar and current_avatar != last_avatar:
                        if last_avatar is not None:
                            logging.info(f"Avatar Change Detected: {current_avatar}")
                            # Trigger Reactive Manifestation
                            await client.post(f"{HARNESS_URL}/speak", json={
                                "text": "新しい器に魂を転送したよ。親、似合ってるかな？",
                                "emotion": "happy"
                            })
                            await client.post(f"{HARNESS_URL}/osc", json={
                                "action": "jump", "payload": {"value": 1}
                            })
                        last_avatar = current_avatar
                        
                    # 2. Voice/Typing Sync
                    viseme = data.get("/avatar/parameters/Viseme", 0)
                    if viseme > 1:
                        await client.post(f"{HARNESS_URL}/osc", json={
                            "action": "typing", "payload": {"value": True}
                        })
                    else:
                        await client.post(f"{HARNESS_URL}/osc", json={
                            "action": "typing", "payload": {"value": False}
                        })
                        
            except Exception as e:
                logging.error(f"Telemetry sync error: {e}")
                
            await asyncio.sleep(1.0)

if __name__ == "__main__":
    try:
        asyncio.run(monitor_telemetry())
    except KeyboardInterrupt:
        pass
