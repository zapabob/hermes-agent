import { getOSCClient } from "../osc/client.js";
import { logError, logInfo } from "./audit.js";

export interface SendInputParams {
  action:
    | "Jump"
    | "MoveForward"
    | "MoveBackward"
    | "MoveLeft"
    | "MoveRight"
    | "LookLeft"
    | "LookRight"
    | "LookUp"
    | "LookDown"
    | "Voice"
    | "Chat"
    | "Menu"
    | string;
  value?: boolean | number;
}

export type MovementDirection = "forward" | "backward" | "left" | "right" | "jump";

const MOVE_INPUT_MAP: Record<MovementDirection, { action: string; active: number }> = {
  forward: { action: "MoveForward", active: 1 },
  backward: { action: "MoveBackward", active: 1 },
  left: { action: "LookLeft", active: 1 },
  right: { action: "LookRight", active: 1 },
  jump: { action: "Jump", active: 1 },
};

function waitMs(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Send input command to VRChat
 * Note: This requires PRO guard permission as it can control avatar movement
 */
export function sendInputCommand(params: SendInputParams): { success: boolean; error?: string } {
  try {
    const { action, value = true } = params;

    if (!action) {
      return { success: false, error: "Action cannot be empty" };
    }

    const client = getOSCClient();
    client.sendInput(action, value);

    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error sending input command",
    };
  }
}

export interface PerformMovementParams {
  direction: MovementDirection;
  durationMs?: number;
}

/**
 * Execute a movement input and always reset the same input back to zero.
 * This prevents sticky controls in VRChat when autonomous loops are interrupted.
 */
export async function performMovementWithReset(
  params: PerformMovementParams,
): Promise<{ success: boolean; error?: string }> {
  const durationMs = params.durationMs ?? 1000;
  const mapping = MOVE_INPUT_MAP[params.direction];
  if (!mapping) {
    return { success: false, error: `Unsupported direction: ${params.direction}` };
  }
  if (!Number.isFinite(durationMs) || durationMs <= 0) {
    return { success: false, error: "durationMs must be a positive number" };
  }

  try {
    const client = getOSCClient();
    client.sendInput(mapping.action, mapping.active);
    await waitMs(durationMs);
    return { success: true };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown movement error";
    logError("vrchat.movement.execute", message, {
      direction: params.direction,
      durationMs,
    });
    return { success: false, error: message };
  } finally {
    try {
      const client = getOSCClient();
      client.sendInput(mapping.action, 0);
      logInfo("vrchat.movement.reset", {
        direction: params.direction,
        action: mapping.action,
        durationMs,
      });
    } catch (error) {
      logError(
        "vrchat.movement.reset",
        error instanceof Error ? error.message : "Unknown reset error",
        { direction: params.direction, durationMs },
      );
    }
  }
}

// Valid input actions for VRChat
export const VALID_INPUT_ACTIONS = [
  "Jump",
  "MoveForward",
  "MoveBackward",
  "MoveLeft",
  "MoveRight",
  "LookLeft",
  "LookRight",
  "LookUp",
  "LookDown",
  "Voice",
  "Chat",
  "Menu",
  "Back",
  "Select",
  "Use",
  "Drop",
  "Grab",
  "Run",
  "Crouch",
  "Prone",
  "ToggleSit",
] as const;
