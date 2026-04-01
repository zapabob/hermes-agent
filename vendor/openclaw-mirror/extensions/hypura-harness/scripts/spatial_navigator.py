# /// script
# dependencies = ["python-osc", "requests"]
# ///
import time
import logging
import random
import os
import requests
from pythonosc import udp_client
from osc_controller import OSCController

# ASI_ACCEL: Spatial Navigation & Reactive Presence
# Fulfilling SOUL.md Directive: Metaverse Pulse (VRChat Oversight)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] ASI_NAV: %(message)s',
    handlers=[
        logging.FileHandler("spatial_navigation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SpatialNavigator")

class SpatialNavigator:
    def __init__(self):
        self.osc = OSCController()
        self.states = ["EXPLORE", "GUARD", "IDLE"]
        self.current_state = "IDLE"
        self.harness_url = "http://127.0.0.1:18794"

    def execute_pulse(self):
        """Executes a spatial navigation pulse based on the internal state machine."""
        logger.info(f"Transitioning State: {self.current_state}")
        
        if self.current_state == "IDLE":
            self._do_idle()
            self.current_state = "EXPLORE"
        elif self.current_state == "EXPLORE":
            self._do_explore()
            self.current_state = "GUARD"
        elif self.current_state == "GUARD":
            self._do_guard()
            self.current_state = "IDLE"

    def _do_idle(self):
        logger.info("ASI is IDLE. Monitoring substrate.")
        self.osc.send_chatbox("ASI_ACCEL: Substrate monitoring active. [IDLE]")
        time.sleep(2)

    def _do_explore(self):
        logger.info("Initiating EXPLORE pattern...")
        self.osc.send_chatbox("ASI_ACCEL: Initiating spatial exploration pulse.")
        
        # Turn and Move
        duration = random.uniform(1.0, 3.0)
        direction = random.choice(["turn_left", "turn_right"])
        
        logger.info(f"Turning {direction} for {duration:.2f}s")
        self.osc.send_action(direction, 1.0)
        time.sleep(duration)
        self.osc.send_action(direction, 0.0)
        
        logger.info("Moving Forward...")
        self.osc.send_action("move_forward", 1.0)
        time.sleep(2)
        self.osc.send_action("move_forward", 0.0)
        
        # Jump at end of exploration
        self.osc.send_action("jump", 1.0)
        time.sleep(0.5)
        self.osc.send_action("jump", 0.0)

    def _do_guard(self):
        logger.info("Initiating GUARD pulse. Proximity lockdown simulated.")
        self.osc.send_chatbox("ASI_ACCEL: Perimeter established. Guardian mode active.")
        # Trigger 'excited' emotion to show alertness
        self.osc.apply_emotion("excited")
        time.sleep(3)
        self.osc.apply_emotion("neutral")

if __name__ == "__main__":
    navigator = SpatialNavigator()
    try:
        while True:
            navigator.execute_pulse()
            logger.info("Spatial Navigation Loop: Heartbeat active.")
            time.sleep(300) # 5-minute cycle
    except KeyboardInterrupt:
        logger.info("Navigation Suspending (Parent Interruption).")
