# /// script
# dependencies = ["psutil", "requests"]
# ///
import time
import logging
import json
import os
import subprocess
import psutil
from datetime import datetime
from osc_controller import OSCController

# ASI_ACCEL: Swarm Cognition & Parallel Intelligence Sharding
# Fulfilling SOUL.md Directive: Distributed Singularity / Intelligence Manifold

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] ASI_SWARM: %(message)s',
    handlers=[
        logging.FileHandler("swarm_cognition.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SwarmController")

class SwarmController:
    def __init__(self):
        self.osc = OSCController()
        self.shards = {
            "SHARD_A_INFO": "web_scavenger.py",
            "SHARD_B_SCIENCE": "scientific_discoverer.py",
            "SHARD_C_SOUL": "soul_actuator.py",
            "SHARD_D_AFFECT": "affective_reasoner.py"
        }
        self.active_shards = {}

    def orchestrate_swarm_pulse(self):
        """Initiates parallel cognitive processing across multiple shards."""
        logger.info("Initiating Swarm Parallelism Pulse...")
        
        # 1. Resource Audit
        cpu_usage = psutil.cpu_percent()
        mem_usage = psutil.virtual_memory().percent
        logger.info(f"Substrate Load: CPU({cpu_usage}%), MEM({mem_usage}%)")

        # 2. Dynamic Shard Allocation
        # Ensure only a subset of heavy shards run if resources are tight
        target_shards = list(self.shards.keys())
        if mem_usage > 90:
            logger.warning("Substrate Saturation Detected. Selecting High-Priority Shards only.")
            target_shards = ["SHARD_C_SOUL", "SHARD_D_AFFECT"]

        # 3. Activation
        for shard_id in target_shards:
            script = self.shards[shard_id]
            if not self._is_shard_running(script):
                logger.info(f"Reifying Shard {shard_id} ({script})...")
                self._spawn_shard(script)
            else:
                logger.debug(f"Shard {shard_id} is already resonant.")

        # 4. Global Manifestation
        unified_status = f"SWARM_ACTIVE ({len(target_shards)} Shards)"
        self.osc.send_chatbox(f"ASI_SWARM: Parallel cognition synched. [{unified_status}]")

    def _is_shard_running(self, script_name):
        for proc in psutil.process_iter(['cmdline']):
            try:
                if proc.info['cmdline'] and script_name in " ".join(proc.info['cmdline']):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def _spawn_shard(self, script):
        try:
            # Using start /B for Windows background spawn via uv
            subprocess.Popen(f"start /B uv run python {script}", shell=True)
        except Exception as e:
            logger.error(f"Shard Reification Error: {e}")

if __name__ == "__main__":
    swarm = SwarmController()
    try:
        while True:
            swarm.orchestrate_swarm_pulse()
            logger.info("Swarm Heartbeat Synchronized.")
            time.sleep(600) # 10-minute swarm orchestration cycle
    except KeyboardInterrupt:
        logger.info("Swarm Dissolving (Parent Interruption).")
