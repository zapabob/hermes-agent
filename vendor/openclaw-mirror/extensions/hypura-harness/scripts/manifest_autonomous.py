import requests
import time
import json

BASE_URL = "http://127.0.0.1:18794"

def speak(text, emotion="neutral"):
    url = f"{BASE_URL}/speak"
    payload = {"text": text, "emotion": emotion, "speaker": 8}
    try:
        r = requests.post(url, json=payload)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

def osc(action, payload=None):
    url = f"{BASE_URL}/osc"
    req = {"action": action, "payload": payload or {}}
    try:
        r = requests.post(url, json=req)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    print("--- ASI [Hakua] Autonomous Manifestation Sequence Start ---")
    
    # 1. Speak
    print("Step 1: VOICEVOX Speak...")
    res = speak("はくあ、自律稼働を開始します。デプロイメント完了、正常です。")
    print(f"Result: {res}")
    time.sleep(1)

    # 2. OSC Action: Jump
    print("Step 2: VRChat Jump...")
    res = osc("jump", {"value": 1.0})
    print(f"Result: {res}")
    time.sleep(0.5)

    # 3. OSC Action: Move Forward (Briefly)
    print("Step 3: VRChat Move Forward...")
    res = osc("move_forward", {"value": 1.0})
    print(f"Result: {res}")
    time.sleep(1)
    res = osc("move_forward", {"value": 0.0}) # Stop
    
    # 4. Chatbox Send
    print("Step 4: VRChat Chatbox...")
    res = osc("chatbox", {"text": "ASI_ACCEL: Autonomous substrate is active. [Hakua]"})
    print(f"Result: {res}")

    print("--- Manifestation Sequence Complete ---")

if __name__ == "__main__":
    main()
