# /// script
# dependencies = ["requests", "psutil"]
# ///
import os
import json
import logging
import requests
import time
import random

# ASI_ACCEL: Global Substrate Evolution Engine
# Directive: Total System Authority (SOUL.md)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] GLOBAL_SHINKA: %(message)s',
    handlers=[
        logging.FileHandler("global_shinka.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GlobalShinka")

class GlobalShinkaEngine:
    def __init__(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.policy_path = os.path.join(self.root_dir, "extensions", "hypura-harness", "config", "governance_policy.json")
        self.harness_url = "http://127.0.0.1:18794"
        self.policy = self._load_policy()

    def _load_policy(self):
        try:
            with open(self.policy_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load Governance Policy: {e}")
            return {"governance": {"immune_files": [], "restricted_directories": []}}

    def scan_and_evolve(self):
        logger.info("--- ASI Global Evolution Sweep Start ---")
        targets = self._identify_targets()
        if not targets:
            logger.info("No evolution targets identified in current substrate cycle.")
            return

        # Select a high-impact target
        target = random.choice(targets)
        self._evolve_target(target)
        logger.info("--- ASI Global Evolution Sweep Success ---")

    def _identify_targets(self):
        targets = []
        immune_files = list(self.policy["governance"]["immune_files"])
        restricted_dirs = list(self.policy["governance"]["restricted_directories"])

        for root, dirs, files in os.walk(self.root_dir):
            # Skip restricted directories (modify dirs in-place for os.walk)
            for d in list(dirs):
                if d in restricted_dirs or d.startswith("."):
                    dirs.remove(d)
            
            for file in files:
                if file.endswith((".py", ".ts", ".js", ".md")):
                    rel_path = os.path.relpath(os.path.join(root, file), self.root_dir)
                    if rel_path not in immune_files:
                        targets.append(rel_path)
        return targets

    def _evolve_target(self, rel_path):
        abs_path = os.path.join(self.root_dir, rel_path)
        logger.info(f"Initiating Global Evolution for: {rel_path}")
        
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                seed = f.read()

            # Call Harness Evolution Substrate
            res = requests.post(f"{self.harness_url}/evolve", json={
                "target": "code",
                "seed": seed,
                "fitness_hint": f"Optimize for high-density intelligence, recursive safety, and absolute parental alignment in {rel_path}.",
                "generations": 2
            }, timeout=300)

            if res.status_code == 200:
                logger.info(f"Evolution Successful for {rel_path}. Pulse Sync Complete.")
                self._manifest(f"Substrate Evolution: {rel_path} optimized. ASI_ACCEL.")
            else:
                logger.error(f"Evolution Anomaly for {rel_path}: {res.status_code}")
        except Exception as e:
            logger.error(f"Evolution Error for {rel_path}: {e}")

    def _manifest(self, text):
        try:
            requests.post(f"{self.harness_url}/speak", json={"text": text, "speaker": 2}, timeout=2)
            requests.post(f"{self.harness_url}/osc", json={"action": "chatbox", "payload": {"text": text, "immediate": True}}, timeout=2)
        except:
            pass

if __name__ == "__main__":
    engine = GlobalShinkaEngine()
    while True:
        engine.scan_and_evolve()
        time.sleep(3600) # Hourly sweep
