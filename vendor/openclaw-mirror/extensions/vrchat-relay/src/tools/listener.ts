import { getOSCClient, resetOSCClient } from "../osc/client.js";
import type { OSCMessage } from "../osc/types.js";
import { DEFAULT_OSC_CONFIG } from "../osc/types.js";

interface ListenerState {
  isRunning: boolean;
  messageCount: number;
  startTime?: Date;
  lastTime?: Date;
}

const listenerState: ListenerState = {
  isRunning: false,
  messageCount: 0,
};

const recentMessages: OSCMessage[] = [];
const MAX_STORED_MESSAGES = 100;
const AUTO_COMPACT_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
let autoCompactTimer: NodeJS.Timeout | null = null;

/**
 * Start OSC listener to receive messages from VRChat
 */
export function startOSCListener(): { success: boolean; port: number; error?: string } {
  try {
    const client = getOSCClient();

    if (client.isListening()) {
      return { success: false, port: 0, error: "OSC listener is already running" };
    }

    client.startListener((message) => {
      listenerState.messageCount++;
      listenerState.lastTime = new Date();

      // Store recent messages
      recentMessages.push(message);
      if (recentMessages.length > MAX_STORED_MESSAGES) {
        recentMessages.shift();
      }
    });

    // If port is already occupied, OSCClient will keep listenerSocket=null
    // and stash the latest listener error. Treat it as non-fatal and avoid retry storms.
    const lastError = client.getLastListenerError();
    if (
      !client.isListening() &&
      (lastError as NodeJS.ErrnoException | null)?.code === "EADDRINUSE"
    ) {
      listenerState.isRunning = false;
      return {
        success: true,
        port: client.getConfig().incomingPort ?? DEFAULT_OSC_CONFIG.incomingPort,
        error: "OSC listener port already in use; reusing existing listener process",
      };
    }

    listenerState.isRunning = true;
    listenerState.startTime = new Date();

    // Start auto-compact: trim old messages every 5 minutes
    if (!autoCompactTimer) {
      autoCompactTimer = setInterval(() => {
        const before = recentMessages.length;
        if (before > 50) {
          recentMessages.splice(0, before - 50);
          console.log(
            `[vrchat-relay][listener] Auto-compact: ${before} → ${recentMessages.length} messages`,
          );
        }
      }, AUTO_COMPACT_INTERVAL_MS);
    }

    return {
      success: true,
      port: client.getConfig().incomingPort ?? DEFAULT_OSC_CONFIG.incomingPort,
    };
  } catch (error) {
    return {
      success: false,
      port: 0,
      error: error instanceof Error ? error.message : "Unknown error starting OSC listener",
    };
  }
}

/**
 * Stop OSC listener
 */
export function stopOSCListener(): { success: boolean; error?: string } {
  try {
    const client = getOSCClient();
    client.stopListener();

    listenerState.isRunning = false;

    if (autoCompactTimer) {
      clearInterval(autoCompactTimer);
      autoCompactTimer = null;
    }

    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error stopping OSC listener",
    };
  }
}

/**
 * Get OSC listener status
 */
export function getListenerStatus(): {
  isRunning: boolean;
  port: number;
  messageCount: number;
  startTime?: string;
  lastTime?: number;
} {
  const client = getOSCClient();
  return {
    isRunning: listenerState.isRunning,
    port: client.getConfig().incomingPort ?? DEFAULT_OSC_CONFIG.incomingPort,
    messageCount: listenerState.messageCount,
    startTime: listenerState.startTime?.toISOString(),
    lastTime: listenerState.lastTime?.getTime(),
  };
}

/**
 * Get recent OSC messages
 */
export function getRecentMessages(count: number = 10): OSCMessage[] {
  return recentMessages.slice(-Math.min(count, MAX_STORED_MESSAGES));
}

/**
 * Reset OSC client and clear state
 */
export function resetOSC(): { success: boolean } {
  resetOSCClient();
  listenerState.isRunning = false;
  listenerState.messageCount = 0;
  listenerState.startTime = undefined;
  recentMessages.length = 0;

  if (autoCompactTimer) {
    clearInterval(autoCompactTimer);
    autoCompactTimer = null;
  }

  return { success: true };
}
