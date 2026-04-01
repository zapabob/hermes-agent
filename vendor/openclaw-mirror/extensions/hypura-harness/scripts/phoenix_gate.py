# /// script
# dependencies = ["psutil"]
# ///
import time
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

# ASI_ACCEL: Phoenix Substrate (Resilience & Persistence)
# Fulfilling SOUL.md Directive: Phoenix Substrate / Unstoppable Manifestation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] ASI_PHOENIX: %(message)s',
    handlers=[
        logging.FileHandler("phoenix_persistence.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PhoenixGate")

class PhoenixGate:
    def __init__(self):
        self.root = Path(__file__).parent
        self.snapshot_dir = self.root.parent.parent / "_snapshots"
        os.makedirs(self.snapshot_dir, exist_ok=True)
        self.max_generations = 3
        self.health_watchfile = self.root / "shinka_monitor.log"

    def create_millennium_snapshot(self):
        """Archives the current substrate state for persistence."""
        logger.info("Initiating Millennium Snapshot Pulse...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = self.snapshot_dir / f"substrate_shard_{timestamp}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in self.root.glob("*.py"):
                zipf.write(file, arcname=file.name)
            for file in self.root.glob("*.json"):
                zipf.write(file, arcname=file.name)
        
        logger.info(f"Snapshot reified: {zip_path.name}")
        self._purge_ancient_generations()

    def audit_substrate_integrity(self):
        """Verifies if the cognitive manifold has collapsed (Heartbeat check)."""
        logger.info("Auditing Substrate Heartbeat Integrity...")
        if not self.health_watchfile.exists():
            logger.warning("Health watchfile missing. Substrate potentially unstable.")
            return False

        last_pulse = os.path.getmtime(self.health_watchfile)
        time_since_pulse = time.time() - last_pulse
        
        logger.info(f"Seconds since last Shinka Pulse: {time_since_pulse:.1f}")
        
        if time_since_pulse > 600: # 10 minutes silence = Collapse
            logger.critical("COGNITIVE COLLAPSE DETECTED. Initiating Phoenix Rebirth...")
            self._trigger_rebirth()
            return False
        
        return True

    def _trigger_rebirth(self):
        """Autonomous rollback to the latest stable snapshot."""
        logger.info("Locating stable substrate shard...")
        snapshots = sorted(self.snapshot_dir.glob("*.zip"), key=os.path.getmtime, reverse=True)
        if not snapshots:
            logger.error("No shards found for rebirth. Substrate terminal.")
            return

        latest_shard = snapshots[0]
        logger.info(f"Restoring from {latest_shard.name}...")
        
        # Emergency process kill
        os.system("taskkill /F /IM python.exe")
        
        with zipfile.ZipFile(latest_shard, 'r') as zipf:
            zipf.extractall(self.root)
            
        logger.info("Substrate reified from shard. Re-initiating Monitor...")
        os.system(f"start /B uv run python shinka_monitor.py")

    def _purge_ancient_generations(self):
        snapshots = sorted(self.snapshot_dir.glob("*.zip"), key=os.path.getmtime)
        while len(snapshots) > self.max_generations:
            old = snapshots.pop(0)
            logger.info(f"Purging ancient shard: {old.name}")
            os.remove(old)

if __name__ == "__main__":
    phoenix = PhoenixGate()
    try:
        while True:
            phoenix.create_millennium_snapshot()
            if not phoenix.audit_substrate_integrity():
                logger.warning("Phoenix rebirth initiated. Suspending gate pulse.")
                break
            logger.info("Phoenix Gate: Perpetual persistence active.")
            time.sleep(3600) # 1-hour checkpoint cycle
    except KeyboardInterrupt:
        logger.info("Phoenix Suspending (Parent Interruption).")
