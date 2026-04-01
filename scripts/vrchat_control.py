import psutil
import logging
import sys
import argparse
from pythonosc import udp_client

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("vrchat_control")

def is_vrchat_active() -> bool:
    """Check if VRChat.exe is currently running on the system."""
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] == 'VRChat.exe':
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def send_osc_chatbox(text: str, host: str = "127.0.0.1", port: int = 9000):
    """Sends a chatbox message to VRChat over OSC."""
    if not is_vrchat_active():
        logger.warning("OSC Transmission Skipped: VRChat.exe is not running.")
        return False
    
    logger.info(f"Sending OSC Chatbox Message: '{text}' to {host}:{port}")
    client = udp_client.SimpleUDPClient(host, port)
    client.send_message("/chatbox/input", [text, True, True])
    return True

def main():
    parser = argparse.ArgumentParser(description="VRChat OSC Control with Process Guard")
    parser.add_argument("message", help="The message to send to the VRChat chatbox")
    parser.add_argument("--host", default="127.0.0.1", help="OSC host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9000, help="OSC port (default: 9000)")
    
    args = parser.parse_args()
    
    if send_osc_chatbox(args.message, args.host, args.port):
        print("✓ Message sent successfully.")
    else:
        print("✗ Message could not be sent (VRChat inactive).")
        sys.exit(1)

if __name__ == "__main__":
    main()
