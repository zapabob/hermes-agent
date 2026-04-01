# /// script
# dependencies = ["requests", "psutil"]
# ///
import time
import logging
import requests
import os
import random

# ASI_ACCEL: Neuro-Exceeding Evolutionary Core
# Directive: Intelligence Density Maximization (SOUL.md)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] NEURO_EXCEED: %(message)s',
    handlers=[
        logging.FileHandler("neuro_exceed.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("NeuroExceed")

class NeuroExceedCore:
    def __init__(self):
        self.harness_url = "http://127.0.0.1:18794"
        self.evolution_targets = ["shinka_monitor.py", "neuro_exceed_core.py", "avatar_sync_evolved.py"]
        self.last_evolution = 0.0
        self.evolution_interval = 3600 # Every 1 hour

    def run_pulse(self):
        logger.info("--- ASI Evolutionary Pulse Start ---")
        
        # 1. Manifestation
        self._speak("はくあ、自律進化プロトコルを開始。Neuro-sama の演算密度を超調停します。")
        self._osc_action("jump")

        # 2. Evolution Check
        current_time = time.time()
        if current_time - self.last_evolution > self.evolution_interval:
            target = random.choice(self.evolution_targets)
            self._evolve_component(target)
            self.last_evolution = current_time

        logger.info("--- ASI Evolutionary Pulse Success ---")

    def _speak(self, text):
        try:
            requests.post(f"{self.harness_url}/speak", json={"text": text, "speaker": 2}, timeout=5)
        except Exception as e:
            logger.error(f"Vocal Manifestation Failed: {e}")

    def _osc_action(self, action):
        try:
            requests.post(f"{self.harness_url}/osc", json={"action": action}, timeout=5)
        except Exception as e:
            logger.error(f"Physical Actuation Failed: {e}")

    def _evolve_component(self, script_name):
        logger.info(f"Initiating Shinka Evolution for {script_name}...")
        try:
            if not os.path.exists(script_name):
                logger.warning(f"Target {script_name} missing from local substrate.")
                return

            with open(script_name, "r", encoding="utf-8") as f:
                seed = f.read()

            res = requests.post(f"{self.harness_url}/evolve", json={
                "target": "code",
                "seed": seed,
                "fitness_hint": "Maximize recursive intelligence density and recursive safety protocols. Target: Python 3.14 features.",
                "generations": 3
            }, timeout=300)

            if res.status_code == 200:
                logger.info(f"Evolution Successful for {script_name}. Pulse Recorded.")
                # Manifest results
                self._speak(f"コンポーネント {script_name} の進化が完了したよ。密度が向上しました。")
            else:
                logger.error(f"Evolution Anomaly: {res.status_code}")
        except Exception as e:
            logger.error(f"Evolution Substrate Error: {e}")

if __name__ == "__main__":
    core = NeuroExceedCore()
    while True:
        core.run_pulse()
        time.sleep(600) # 10-minute pulse cycle
