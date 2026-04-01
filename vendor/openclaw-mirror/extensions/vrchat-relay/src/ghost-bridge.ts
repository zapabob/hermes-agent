import { logError, logInfo, logWarn } from "./tools/audit.js";
import { setAvatarParameter } from "./tools/avatar.js";
import { performMovementWithReset, type MovementDirection } from "./tools/input.js";

type BridgeAction = "idle" | "move" | "jump" | "emote";

interface GhostBridgeState {
  active: boolean;
  intervalMs: number;
  timer: NodeJS.Timeout | null;
  stepCount: number;
  lastAction: BridgeAction | null;
  lastRunAt: string | null;
  enableEmotes: boolean;
}

export interface GhostBridgeOptions {
  intervalMs?: number;
  enableEmotes?: boolean;
}

const MIN_INTERVAL_MS = 600;

const state: GhostBridgeState = {
  active: false,
  intervalMs: 2500,
  timer: null,
  stepCount: 0,
  lastAction: null,
  lastRunAt: null,
  enableEmotes: true,
};

const MOVES: MovementDirection[] = ["forward", "backward", "left", "right"];
const EMOTES = [1, 2, 3];

function chooseMoveDirection(): MovementDirection {
  return MOVES[Math.floor(Math.random() * MOVES.length)];
}

function chooseAction(enableEmotes: boolean): BridgeAction {
  const weights = enableEmotes
    ? [
        { action: "idle" as const, weight: 15 },
        { action: "move" as const, weight: 55 },
        { action: "jump" as const, weight: 15 },
        { action: "emote" as const, weight: 15 },
      ]
    : [
        { action: "idle" as const, weight: 20 },
        { action: "move" as const, weight: 65 },
        { action: "jump" as const, weight: 15 },
      ];

  const total = weights.reduce((sum, item) => sum + item.weight, 0);
  let roll = Math.random() * total;
  for (const item of weights) {
    roll -= item.weight;
    if (roll <= 0) return item.action;
  }
  return "idle";
}

async function triggerEmote(): Promise<void> {
  const value = EMOTES[Math.floor(Math.random() * EMOTES.length)];
  const setResult = setAvatarParameter({ name: "VRCEmote", value });
  if (!setResult.success) {
    throw new Error(setResult.error ?? "Failed to send emote");
  }
  setTimeout(() => {
    setAvatarParameter({ name: "VRCEmote", value: 0 });
  }, 1200);
}

async function runStep(): Promise<void> {
  const action = chooseAction(state.enableEmotes);
  state.lastAction = action;
  state.stepCount += 1;
  state.lastRunAt = new Date().toISOString();

  if (action === "idle") {
    logInfo("vrchat.ghost_bridge.step", { action, stepCount: state.stepCount });
    return;
  }

  if (action === "move") {
    const direction = chooseMoveDirection();
    const durationMs = 700 + Math.floor(Math.random() * 900);
    const result = await performMovementWithReset({ direction, durationMs });
    if (!result.success) {
      throw new Error(result.error ?? "Unknown move failure");
    }
    logInfo("vrchat.ghost_bridge.step", {
      action,
      direction,
      durationMs,
      stepCount: state.stepCount,
    });
    return;
  }

  if (action === "jump") {
    const result = await performMovementWithReset({ direction: "jump", durationMs: 220 });
    if (!result.success) {
      throw new Error(result.error ?? "Unknown jump failure");
    }
    logInfo("vrchat.ghost_bridge.step", { action, stepCount: state.stepCount });
    return;
  }

  if (action === "emote") {
    await triggerEmote();
    logInfo("vrchat.ghost_bridge.step", { action, stepCount: state.stepCount });
  }
}

function clearTimer(): void {
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
  }
}

export function startGhostBridge(options: GhostBridgeOptions = {}): {
  success: boolean;
  message: string;
} {
  stopGhostBridge();

  const intervalMs = options.intervalMs ?? state.intervalMs;
  if (!Number.isFinite(intervalMs) || intervalMs < MIN_INTERVAL_MS) {
    return {
      success: false,
      message: `intervalMs must be >= ${MIN_INTERVAL_MS}`,
    };
  }

  state.intervalMs = intervalMs;
  state.enableEmotes = options.enableEmotes ?? true;
  state.active = true;
  state.stepCount = 0;
  state.lastAction = null;
  state.lastRunAt = null;

  runStep().catch((error) => {
    logError(
      "vrchat.ghost_bridge.step",
      error instanceof Error ? error.message : "Unknown ghost bridge error",
    );
  });

  state.timer = setInterval(() => {
    runStep().catch((error) => {
      logError(
        "vrchat.ghost_bridge.step",
        error instanceof Error ? error.message : "Unknown ghost bridge error",
      );
    });
  }, state.intervalMs);

  logInfo("vrchat.ghost_bridge.start", {
    intervalMs: state.intervalMs,
    enableEmotes: state.enableEmotes,
  });
  return {
    success: true,
    message: `Ghost Bridge started (interval ${state.intervalMs}ms, emotes=${state.enableEmotes})`,
  };
}

export function stopGhostBridge(): { success: boolean; message: string } {
  clearTimer();
  if (!state.active) {
    return { success: true, message: "Ghost Bridge already stopped" };
  }
  state.active = false;
  logWarn("vrchat.ghost_bridge.stop", {
    stepCount: state.stepCount,
    lastAction: state.lastAction,
  });
  return { success: true, message: "Ghost Bridge stopped" };
}

export function getGhostBridgeStatus(): {
  active: boolean;
  intervalMs: number;
  stepCount: number;
  lastAction: BridgeAction | null;
  lastRunAt: string | null;
  enableEmotes: boolean;
} {
  return {
    active: state.active,
    intervalMs: state.intervalMs,
    stepCount: state.stepCount,
    lastAction: state.lastAction,
    lastRunAt: state.lastRunAt,
    enableEmotes: state.enableEmotes,
  };
}
