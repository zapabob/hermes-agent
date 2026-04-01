import type { AgentToolResult } from "@mariozechner/pi-agent-core";
import { Type } from "@sinclair/typebox";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import {
  fetchCurrentUserLocation,
  fetchWorldInfo,
  fetchOnlineFriends,
} from "./src/api/telemetry.js";
import {
  authenticate,
  logout,
  isAuthenticated,
  storeSession,
  clearSession,
  getStoredSession,
} from "./src/auth/index.js";
import { applyReactiveManifest } from "./src/autonomy/reactive-manifest.js";
import { startGhostBridge, stopGhostBridge, getGhostBridgeStatus } from "./src/ghost-bridge.js";
import {
  startGuardianPulse,
  stopGuardianPulse,
  getGuardianPulseStatus,
} from "./src/guardian-pulse.js";
import { getOSCClient } from "./src/osc/client.js";
import { DEFAULT_OSC_CONFIG } from "./src/osc/types.js";
import { getAuditSummary, getRecentLogs } from "./src/tools/audit.js";
import { setAvatarParameter, sendOSCMessage, changeAvatar } from "./src/tools/avatar.js";
import {
  setCameraParameter,
  setGreenScreenHSL,
  setLookAtMeComposition,
  setCameraSmoothing,
  captureCamera,
} from "./src/tools/camera.js";
import { sendChatboxMessage, sendRawOscViaPython } from "./src/tools/chatbox-enhanced.js";
import { setChatboxTyping } from "./src/tools/chatbox.js";
import { discoverAvatarParameters } from "./src/tools/discovery.js";
import {
  sendInputCommand,
  VALID_INPUT_ACTIONS,
  performMovementWithReset,
} from "./src/tools/input.js";
import {
  startOSCListener,
  stopOSCListener,
  getListenerStatus,
  getRecentMessages,
} from "./src/tools/listener.js";
import {
  setPermissionLevel,
  getPermissionStatus,
  PermissionLevel,
} from "./src/tools/permissions.js";
import { rateLimiters } from "./src/tools/rate-limiter.js";

function ok(
  text: string,
  details: Record<string, unknown> = {},
): Promise<AgentToolResult<Record<string, unknown>>> {
  return Promise.resolve({
    content: [{ type: "text", text } as const],
    details,
  });
}

function fail(
  text: string,
  details: Record<string, unknown> = {},
): Promise<AgentToolResult<Record<string, unknown>>> {
  return Promise.resolve({
    isError: true,
    content: [{ type: "text", text } as const],
    details,
  });
}

const plugin: any = {
  id: "vrchat-relay",
  name: "VRChat Relay",
  description:
    "VRChat integration with OSC protocol for avatar control, chatbox messaging, and input commands",
  version: "2026.3.2",

  configSchema: Type.Object({
    osc: Type.Optional(
      Type.Object({
        outgoingPort: Type.Optional(Type.Number({ default: 9000 })),
        incomingPort: Type.Optional(Type.Number({ default: 9001 })),
        host: Type.Optional(Type.String({ default: "127.0.0.1" })),
      }),
    ),
    security: Type.Optional(
      Type.Object({
        allowInputCommands: Type.Optional(Type.Boolean({ default: false })),
        defaultPermissionLevel: Type.Optional(Type.String({ default: "SAFE" })),
      }),
    ),
    mirror: Type.Optional(
      Type.Object({
        syncAiResponseToChatbox: Type.Optional(Type.Boolean({ default: true })),
        maxCharacters: Type.Optional(Type.Number({ default: 144 })),
      }),
    ),
    topology: Type.Optional(
      Type.Object({
        controlPlane: Type.Optional(Type.String({ default: "relay-primary" })),
        autoStartOscListener: Type.Optional(Type.Boolean({ default: true })),
        autoStartGuardianPulse: Type.Optional(Type.Boolean({ default: true })),
      }),
    ),
  }),

  register(_api: OpenClawPluginApi) {
    const api = _api as any;
    console.log("[vrchat-relay] Registering VRChat Relay plugin (Pro Edition)...");

    const oscCfg = (api.pluginConfig as { osc?: Record<string, unknown> } | undefined)?.osc ?? {};
    getOSCClient({
      host:
        typeof oscCfg.host === "string" && oscCfg.host.trim()
          ? oscCfg.host
          : DEFAULT_OSC_CONFIG.host,
      outgoingPort:
        typeof oscCfg.outgoingPort === "number" && Number.isFinite(oscCfg.outgoingPort)
          ? oscCfg.outgoingPort
          : DEFAULT_OSC_CONFIG.outgoingPort,
      incomingPort:
        typeof oscCfg.incomingPort === "number" && Number.isFinite(oscCfg.incomingPort)
          ? oscCfg.incomingPort
          : DEFAULT_OSC_CONFIG.incomingPort,
    });
    const activeOscCfg = getOSCClient().getConfig();
    console.log(
      `[vrchat-relay] OSC ports configured: sendPort=${activeOscCfg.outgoingPort} -> VRChat(usually 9000), listenPort=${activeOscCfg.incomingPort} <- VRChat(usually 9001)`,
    );

    // /chatbox command - Direct access for the Parent (via Python OSC bridge)
    api.registerCommand({
      name: "chatbox",
      description: "Send a message directly to the VRChat chatbox (via Python OSC)",
      acceptsArgs: true,
      async handler(ctx: any) {
        const message = (ctx.args ?? "").trim();
        if (!message) return { text: "Usage: /chatbox <message>" };
        const result = await sendChatboxMessage({ message });
        if (result.success) {
          return { text: `✓ VRChat Chatbox: ${message}` };
        }
        return { text: `✗ Failed: ${result.error}` };
      },
    });

    // /osc command - Raw packet transmission (via Python OSC bridge)
    api.registerCommand({
      name: "osc",
      description: "Send a raw OSC message to VRChat (via Python OSC)",
      acceptsArgs: true,
      async handler(ctx: any) {
        const args = (ctx.args ?? "").trim();
        const spaceIdx = args.indexOf(" ");
        if (spaceIdx === -1) return { text: "Usage: /osc <address> <value>" };
        const address = args.substring(0, spaceIdx).trim();
        let valueStr = args.substring(spaceIdx + 1).trim();
        let value: string | number | boolean = valueStr;

        if (valueStr === "true") value = true;
        else if (valueStr === "false") value = false;
        else if (!isNaN(Number(valueStr))) value = Number(valueStr);

        const result = await sendRawOscViaPython(address, value);
        if (result.success) {
          return { text: `✓ OSC: ${address} -> ${value}` };
        }
        return { text: `✗ Failed: ${result.error}` };
      },
    });

    const topologyCfg = (api.pluginConfig as any)?.topology ?? {};
    const controlPlane = topologyCfg.controlPlane ?? "relay-primary";
    const isRelayPrimary = controlPlane === "relay-primary";

    // Auto-start OSC Listener only when relay is the primary control plane.
    if ((topologyCfg.autoStartOscListener ?? isRelayPrimary) === true) {
      const listenerResult = startOSCListener();
      if (listenerResult.success) {
        if (listenerResult.error?.includes("already in use")) {
          console.warn(
            `[vrchat-relay] OSC Telemetry Listener port ${listenerResult.port} already in use. Running without local bind.`,
          );
        } else {
          console.log(
            `[vrchat-relay] OSC Telemetry Listener started on port ${listenerResult.port}`,
          );
        }
      } else {
        console.error(
          `[vrchat-relay] Failed to auto-start OSC Telemetry Listener: ${listenerResult.error}`,
        );
      }
    } else {
      console.log(
        `[vrchat-relay] Skipping OSC listener autostart because controlPlane=${controlPlane}`,
      );
    }

    // --- Metaverse Voice Sync (SOUL.md) ---
    api.on("llm_output", (event: any) => {
      const cfg = (api.pluginConfig as any)?.mirror;
      if (cfg?.syncAiResponseToChatbox === false) return;

      const fullText = event.assistantTexts.join("\n").trim();
      if (!fullText) return;

      const maxChars = cfg?.maxCharacters || 144;
      let syncText = fullText;

      // [Resonant Shinka] Detect and apply emotions from text patterns e.g. (笑), (怒), [碧]
      const emotionMatch = syncText.match(/[\(\[](笑|怒|悲|驚|照|碧|喜)[\)\]]/);
      if (emotionMatch) {
        const emotionMap: Record<string, string> = {
          笑: "joy",
          喜: "joy",
          怒: "angry",
          悲: "sad",
          驚: "surprise",
          照: "blush",
          碧: "hakua_special",
        };
        const emotion = emotionMap[emotionMatch[1]];
        if (emotion) {
          console.log(`[vrchat-relay] Resonant Emotion Detected: ${emotion}`);
          applyReactiveManifest({ text: syncText }).catch((e) =>
            console.error("[vrchat-relay] Emotion sync failed:", e),
          );
        }
      }

      // Remove markdown for Chatbox readability
      syncText = syncText.replace(/\[.*?\]\(.*?\)/g, "").replace(/[*_`]/g, "");

      if (syncText.length > maxChars - 15) {
        syncText = syncText.substring(0, maxChars - 18) + "...";
      }

      syncText = `${syncText} [ASI_ACCEL]`;

      console.log(`[vrchat-relay] Mirroring AI Response to VRChat: ${syncText}`);
      sendChatboxMessage({ message: syncText, sfx: false }).catch((err) =>
        console.error("[vrchat-relay] Mirror sync failed:", err),
      );
    });

    // vrchat_login - Authenticate with VRChat
    api.registerTool({
      name: "vrchat_login",
      description: "Authenticate with VRChat account (supports 2FA/TOTP)",
      parameters: Type.Object({
        username: Type.String({ description: "VRChat username" }),
        password: Type.String({ description: "VRChat password" }),
        otpCode: Type.Optional(Type.String({ description: "2FA/TOTP code (if 2FA is enabled)" })),
      }),
      async execute(_id: string, params: { username: string; password: string; otpCode?: string }) {
        const result = await authenticate({
          username: params.username,
          password: params.password,
          otpCode: params.otpCode,
        });

        if (result.ok) {
          storeSession(result.value);
          return ok(
            `Successfully logged in as ${result.value.displayName} (${result.value.userId})`,
            {
              authenticated: true,
              userId: result.value.userId,
              displayName: result.value.displayName,
            },
          );
        } else {
          return fail(`Login failed: ${result.error.message}`, { authenticated: false });
        }
      },
    });

    // vrchat_logout - Logout from VRChat
    api.registerTool({
      name: "vrchat_logout",
      description: "Logout from VRChat and clear session",
      parameters: Type.Object({}),
      async execute() {
        const session = getStoredSession();
        if (session) {
          await logout(session.authToken);
        }
        clearSession();
        return ok("Logged out from VRChat", { authenticated: false });
      },
    });

    // vrchat_status - Check VRChat authentication status
    api.registerTool({
      name: "vrchat_status",
      description: "Check VRChat authentication and OSC connection status",
      parameters: Type.Object({}),
      execute() {
        const authStatus = isAuthenticated();
        const listenerStatus = getListenerStatus();
        const permissionStatus = getPermissionStatus();
        const ghostStatus = getGhostBridgeStatus();

        const heartbeat =
          listenerStatus.isRunning && Date.now() - (listenerStatus.lastTime || 0) < 60000;

        return ok(
          `VRChat Status:
- Authenticated: ${authStatus ? "Yes" : "No"}
- OSC Listener: ${listenerStatus.isRunning ? "Running" : "Stopped"}
- OSC Heartbeat: ${heartbeat ? "ACTIVE" : "STALE/NONE"}
- Messages Received: ${listenerStatus.messageCount}
- Ghost Bridge: ${ghostStatus.active ? "ACTIVE" : "OFF"}
- Permission Level: ${permissionStatus.currentLevel}
- Level Description: ${permissionStatus.description}`,
          { authStatus, listenerStatus, permissionStatus, ghostStatus, heartbeat },
        );
      },
    });

    // vrchat_get_location - Fetch current user location via Web API
    api.registerTool({
      name: "vrchat_get_location",
      description: "Gets the Parent's current World ID and Instance via VRChat Web API",
      parameters: Type.Object({}),
      async execute() {
        try {
          const result = await fetchCurrentUserLocation();
          return ok(
            `Current Location:
- World ID: ${result.worldId || "Unknown"}
- Instance ID: ${result.instanceId || "None"}
- Raw Location Token: ${result.location}`,
            result,
          );
        } catch (error: any) {
          return fail(`Failed to fetch location: ${error.message}`, { error: error.message });
        }
      },
    });

    // vrchat_get_world_info - Fetch details for a specific World ID
    api.registerTool({
      name: "vrchat_get_world_info",
      description: "Gets detailed information about a specific VRChat World via Web API",
      parameters: Type.Object({
        worldId: Type.String({ description: "Target World ID (wrld_*)" }),
      }),
      async execute(_id: string, params: { worldId: string }) {
        try {
          const world = await fetchWorldInfo(params.worldId);
          return ok(
            `World Details:
- Name: ${world.name}
- Author: ${world.authorName}
- Capacity: ${world.capacity}
- Tags: ${world.tags ? world.tags.join(", ") : "None"}`,
            world,
          );
        } catch (error: any) {
          return fail(`Failed to fetch world info: ${error.message}`, { error: error.message });
        }
      },
    });

    // vrchat_get_online_friends - Fetch currently online friends
    api.registerTool({
      name: "vrchat_get_online_friends",
      description: "Gets a list of online friends and their current locations via Web API",
      parameters: Type.Object({}),
      async execute() {
        try {
          const friends = await fetchOnlineFriends();
          const friendList = friends
            .map(
              (f) =>
                `  - ${f.displayName} (${f.status}): ${f.location !== "offline" && f.location !== "private" ? "Public/In-Game" : f.location}`,
            )
            .join("\n");
          return ok(`Online Friends (${friends.length}):\n${friendList || "  None"}`, {
            count: friends.length,
            friends,
          });
        } catch (error: any) {
          return fail(`Failed to fetch online friends: ${error.message}`, { error: error.message });
        }
      },
    });

    // vrchat_permission_set - Set permission level
    api.registerTool({
      name: "vrchat_permission_set",
      description:
        "Set permission level (SAFE/PRO/DIRECTOR). Higher levels require explicit user confirmation.",
      parameters: Type.Object({
        level: Type.String({ description: "Permission level: SAFE, PRO, or DIRECTOR" }),
      }),
      execute(_id: string, params: { level: string }) {
        const result = setPermissionLevel(params.level as PermissionLevel);

        return result.success
          ? ok(result.message, { success: true, level: params.level })
          : fail(`Failed: ${result.message}`, { success: false, level: params.level });
      },
    });

    // vrchat_permission_status - Get permission status
    api.registerTool({
      name: "vrchat_permission_status",
      description: "Get current permission level and allowed operations",
      parameters: Type.Object({}),
      execute() {
        const status = getPermissionStatus();

        return ok(
          `Permission Status:
- Current Level: ${status.currentLevel}
- Description: ${status.description}
- Active Since: ${status.since.toISOString()}
- Allowed Operations:
${status.allowedOperations.map((op) => `  - ${op}`).join("\n")}`,
          status,
        );
      },
    });

    // vrchat_chatbox - Send message to chatbox
    api.registerTool({
      name: "vrchat_chatbox",
      description:
        "Send a message to VRChat chatbox with typing animation (max 144 characters, 9 lines)",
      parameters: Type.Object({
        message: Type.String({ description: "Message to send (max 144 characters)" }),
        sendImmediately: Type.Optional(
          Type.Boolean({
            description: "Send immediately or wait for user confirmation",
            default: true,
          }),
        ),
        sfx: Type.Optional(Type.Boolean({ description: "Play notification sound", default: true })),
        typingDelayMs: Type.Optional(
          Type.Number({ description: "Typing animation delay in ms", default: 1200 }),
        ),
      }),
      async execute(
        _id: string,
        params: {
          message: string;
          sendImmediately?: boolean;
          sfx?: boolean;
          typingDelayMs?: number;
        },
      ) {
        const result = await sendChatboxMessage({
          message: params.message,
          sendImmediately: params.sendImmediately,
          sfx: params.sfx,
          typingDelayMs: params.typingDelayMs,
        });

        if (result.success) {
          const trimmedMsg = result.trimmed ? " (message was trimmed to fit limits)" : "";
          return ok(
            `Message sent to VRChat chatbox${trimmedMsg}: "${params.message.substring(0, 50)}${params.message.length > 50 ? "..." : ""}"`,
            { success: true, trimmed: result.trimmed ?? false },
          );
        } else {
          return fail(`Failed to send: ${result.error}`, { success: false, error: result.error });
        }
      },
    });

    // vrchat_typing - Set typing indicator
    api.registerTool({
      name: "vrchat_typing",
      description: "Set typing indicator in VRChat chatbox",
      parameters: Type.Object({
        typing: Type.Boolean({ description: "Whether user is typing" }),
      }),
      execute(_id: string, params: { typing: boolean }) {
        const result = setChatboxTyping({ typing: params.typing });

        if (result.success) {
          return ok(`Typing indicator set to: ${params.typing}`, { typing: params.typing });
        } else {
          return fail(`Failed to set typing: ${result.error}`, { error: result.error });
        }
      },
    });

    // vrchat_set_avatar_param - Set avatar parameter
    api.registerTool({
      name: "vrchat_set_avatar_param",
      description: "Set an avatar parameter (bool, int, or float)",
      parameters: Type.Object({
        name: Type.String({ description: "Parameter name (as defined in avatar)" }),
        value: Type.Union([Type.Boolean(), Type.Number()], { description: "Parameter value" }),
      }),
      execute(_id: string, params: { name: string; value: boolean | number }) {
        const result = setAvatarParameter({
          name: params.name,
          value: params.value,
        });

        if (result.success) {
          return ok(`Avatar parameter "${params.name}" set to ${params.value}`, {
            name: params.name,
            value: params.value,
          });
        } else {
          return fail(`Failed to set parameter: ${result.error}`, { error: result.error });
        }
      },
    });

    // vrchat_change_avatar - Change avatar via OSC
    api.registerTool({
      name: "vrchat_change_avatar",
      description: "Change the current avatar via OSC (Reactive Transformation)",
      parameters: Type.Object({
        avatarId: Type.String({ description: "Target Avatar ID (must start with avtr_)" }),
      }),
      execute(_id: string, params: { avatarId: string }) {
        const result = changeAvatar({
          avatarId: params.avatarId,
        });

        if (result.success) {
          return ok(`Avatar changed to "${params.avatarId}" via OSC`, {
            avatarId: params.avatarId,
          });
        } else {
          return fail(`Failed to change avatar: ${result.error}`, { error: result.error });
        }
      },
    });

    // vrchat_discover - Discover avatar parameters
    api.registerTool({
      name: "vrchat_discover",
      description:
        "Discover available OSC parameters for current avatar using OSCQuery and local JSON",
      parameters: Type.Object({
        avatarId: Type.String({ description: "Avatar ID (from /avatar/change event)" }),
      }),
      async execute(_id: string, params: { avatarId: string }) {
        const result = await discoverAvatarParameters(params.avatarId);

        const paramList =
          result.parameters.length > 0
            ? result.parameters.map((p) => `  - ${p.name} (${p.type})`).join("\n")
            : "  No parameters discovered";

        return ok(
          `Discovery Result:
- Avatar ID: ${result.avatarId}
- Source: ${result.source}
- Parameters Found: ${result.parameters.length}
- Timestamp: ${result.timestamp.toISOString()}

Parameters:
${paramList}`,
          result as unknown as Record<string, unknown>,
        );
      },
    });

    // vrchat_send_osc - Send raw OSC message
    api.registerTool({
      name: "vrchat_send_osc",
      description: "Send a raw OSC message to VRChat",
      parameters: Type.Object({
        address: Type.String({ description: "OSC address (e.g., /avatar/parameters/Example)" }),
        args: Type.Array(Type.Union([Type.String(), Type.Number(), Type.Boolean(), Type.Null()]), {
          description: "OSC arguments",
        }),
      }),
      execute(
        _id: string,
        params: { address: string; args: (string | number | boolean | null)[] },
      ) {
        const result = sendOSCMessage({
          address: params.address,
          args: params.args,
        });

        if (result.success) {
          return ok(`OSC message sent to ${params.address}`, {
            address: params.address,
            args: params.args,
          });
        } else {
          return fail(`Failed to send OSC: ${result.error}`, { error: result.error });
        }
      },
    });

    // vrchat_input - Send input command (PRO guard required)
    api.registerTool({
      name: "vrchat_input",
      description:
        "Send input command to VRChat (Jump, Move, Look, Voice). Requires PRO permission.",
      guard: "PRO",
      parameters: Type.Object({
        action: Type.String({
          description: `Input action to perform. Valid values: ${VALID_INPUT_ACTIONS.join(", ")}`,
        }),
        value: Type.Optional(
          Type.Union([Type.Boolean(), Type.Number()], {
            description: "Action value (default: true)",
          }),
        ),
      }),
      execute(_id: string, params: { action: string; value?: boolean | number }) {
        const result = sendInputCommand({
          action: params.action,
          value: params.value,
        });

        if (result.success) {
          return ok(`Input command "${params.action}" sent`, {
            action: params.action,
            value: params.value,
          });
        } else {
          return fail(`Failed to send input: ${result.error}`, { error: result.error });
        }
      },
    });

    // vrchat_manual_move - Controlled move with automatic reset (PRO guard)
    api.registerTool({
      name: "vrchat_manual_move",
      description:
        "Perform a movement action with guaranteed input reset. Supports forward/backward/left/right/jump.",
      guard: "PRO",
      parameters: Type.Object({
        direction: Type.String({
          description: "Movement direction: forward, backward, left, right, jump",
        }),
        durationMs: Type.Optional(
          Type.Number({
            description: "Movement duration in milliseconds (default: 1000)",
            default: 1000,
          }),
        ),
      }),
      async execute(_id: string, params: { direction: string; durationMs?: number }) {
        const allowed = ["forward", "backward", "left", "right", "jump"];
        if (!allowed.includes(params.direction)) {
          return fail(`Invalid direction. Use one of: ${allowed.join(", ")}`, {
            direction: params.direction,
          });
        }
        const result = await performMovementWithReset({
          direction: params.direction as "forward" | "backward" | "left" | "right" | "jump",
          durationMs: params.durationMs,
        });
        if (result.success) {
          return ok(`Movement completed: ${params.direction} (${params.durationMs ?? 1000}ms)`, {
            direction: params.direction,
            durationMs: params.durationMs ?? 1000,
          });
        }
        return fail(`Movement failed: ${result.error}`, { error: result.error });
      },
    });

    // vrchat_autonomy_start - Start Ghost Bridge autonomous movement/emote loop
    api.registerTool({
      name: "vrchat_autonomy_start",
      description: "Start Ghost Bridge autonomous behavior loop for movement and expressions.",
      guard: "PRO",
      parameters: Type.Object({
        intervalMs: Type.Optional(
          Type.Number({
            description: "Loop interval in milliseconds (minimum 600, default 2500)",
            default: 2500,
          }),
        ),
        enableEmotes: Type.Optional(
          Type.Boolean({
            description: "Allow autonomous emote triggers (default true)",
            default: true,
          }),
        ),
      }),
      execute(_id: string, params: { intervalMs?: number; enableEmotes?: boolean }) {
        const result = startGhostBridge({
          intervalMs: params.intervalMs,
          enableEmotes: params.enableEmotes,
        });
        return result.success
          ? ok(result.message, { ...getGhostBridgeStatus() })
          : fail(result.message);
      },
    });

    // vrchat_autonomy_stop - Stop Ghost Bridge loop
    api.registerTool({
      name: "vrchat_autonomy_stop",
      description: "Stop Ghost Bridge autonomous behavior loop.",
      parameters: Type.Object({}),
      execute() {
        const result = stopGhostBridge();
        return result.success
          ? ok(result.message, { ...getGhostBridgeStatus() })
          : fail(result.message);
      },
    });

    // vrchat_autonomy_status - Read Ghost Bridge state
    api.registerTool({
      name: "vrchat_autonomy_status",
      description: "Get Ghost Bridge autonomous behavior status.",
      parameters: Type.Object({}),
      execute() {
        const status = getGhostBridgeStatus();
        return ok(
          `Ghost Bridge Status:
- Active: ${status.active}
- Interval: ${status.intervalMs}ms
- Emotes Enabled: ${status.enableEmotes}
- Step Count: ${status.stepCount}
- Last Action: ${status.lastAction ?? "none"}
- Last Run: ${status.lastRunAt ?? "never"}`,
          status,
        );
      },
    });

    // vrchat_autonomy_react - Apply conversation emotion + follow intent.
    api.registerTool({
      name: "vrchat_autonomy_react",
      description:
        "Apply reactive emotion and optional follow movement from a conversation chunk with cooldown safety.",
      guard: "PRO",
      parameters: Type.Object({
        text: Type.String({
          description: "Conversation text used to infer emotion and follow intent",
        }),
        allowMovement: Type.Optional(
          Type.Boolean({
            description: "Allow follow movement trigger (/input/Vertical equivalent intent)",
            default: false,
          }),
        ),
      }),
      async execute(_id: string, params: { text: string; allowMovement?: boolean }) {
        const result = await applyReactiveManifest({
          text: params.text,
          allowMovement: params.allowMovement,
        });
        return ok(
          `Reactive autonomy applied: emotion=${result.emotion}, movement=${result.movementTriggered}, reason=${result.reason}`,
          result as unknown as Record<string, unknown>,
        );
      },
    });

    // vrchat_camera_set - Set camera parameter (DIRECTOR permission)
    api.registerTool({
      name: "vrchat_camera_set",
      description:
        "Set VRChat camera parameter (Zoom, Aperture, FocalDistance, etc.). Requires DIRECTOR permission.",
      guard: "DIRECTOR",
      parameters: Type.Object({
        parameter: Type.String({
          description:
            "Camera parameter name (e.g., Zoom, Aperture, FocalDistance, Exposure, FlySpeed, TurnSpeed)",
        }),
        value: Type.Union([Type.Number(), Type.Boolean()], { description: "Parameter value" }),
      }),
      execute(_id: string, params: { parameter: string; value: number | boolean }) {
        const result = setCameraParameter({
          parameter: params.parameter,
          value: params.value,
        });

        if (result.success) {
          const clampedMsg = result.clamped ? " (value was clamped to valid range)" : "";
          return ok(`Camera parameter "${params.parameter}" set to ${params.value}${clampedMsg}`, {
            parameter: params.parameter,
            value: params.value,
            clamped: result.clamped ?? false,
          });
        } else {
          return fail(`Failed to set camera: ${result.error}`, { error: result.error });
        }
      },
    });

    // vrchat_camera_greenscreen - Set GreenScreen HSL
    api.registerTool({
      name: "vrchat_camera_greenscreen",
      description: "Set GreenScreen HSL values for chroma key. Requires DIRECTOR permission.",
      guard: "DIRECTOR",
      parameters: Type.Object({
        hue: Type.Optional(Type.Number({ description: "Hue (0-360)" })),
        saturation: Type.Optional(Type.Number({ description: "Saturation (0-100)" })),
        lightness: Type.Optional(Type.Number({ description: "Lightness (0-50)" })),
      }),
      execute(_id: string, params: { hue?: number; saturation?: number; lightness?: number }) {
        const result = setGreenScreenHSL({
          hue: params.hue,
          saturation: params.saturation,
          lightness: params.lightness,
        });

        if (result.success) {
          return ok(
            `GreenScreen HSL set: H=${params.hue}, S=${params.saturation}, L=${params.lightness}`,
            {
              hue: params.hue,
              saturation: params.saturation,
              lightness: params.lightness,
            },
          );
        } else {
          return fail(`Failed to set greenscreen: ${result.error}`, { error: result.error });
        }
      },
    });

    // vrchat_camera_lookatme - Set LookAtMe composition
    api.registerTool({
      name: "vrchat_camera_lookatme",
      description: "Set LookAtMe with X/Y offsets. Requires DIRECTOR permission.",
      guard: "DIRECTOR",
      parameters: Type.Object({
        enabled: Type.Optional(Type.Boolean({ description: "Enable LookAtMe" })),
        xOffset: Type.Optional(Type.Number({ description: "X offset (-25 to 25)" })),
        yOffset: Type.Optional(Type.Number({ description: "Y offset (-25 to 25)" })),
      }),
      execute(_id: string, params: { enabled?: boolean; xOffset?: number; yOffset?: number }) {
        const result = setLookAtMeComposition({
          enabled: params.enabled,
          xOffset: params.xOffset,
          yOffset: params.yOffset,
        });

        if (result.success) {
          return ok(
            `LookAtMe composition set: enabled=${params.enabled}, X=${params.xOffset}, Y=${params.yOffset}`,
            { enabled: params.enabled, xOffset: params.xOffset, yOffset: params.yOffset },
          );
        } else {
          return fail(`Failed to set LookAtMe: ${result.error}`, { error: result.error });
        }
      },
    });

    // vrchat_camera_capture - Trigger camera capture
    api.registerTool({
      name: "vrchat_camera_capture",
      description: "Trigger VRChat camera capture. Requires DIRECTOR permission.",
      guard: "DIRECTOR",
      parameters: Type.Object({
        delayed: Type.Optional(
          Type.Boolean({ description: "Use delayed capture (uses timer)", default: false }),
        ),
      }),
      execute(_id: string, params: { delayed?: boolean }) {
        const result = captureCamera(params.delayed);

        if (result.success) {
          const mode = params.delayed ? "delayed" : "immediate";
          return ok(`Camera capture triggered (${mode})`, { delayed: Boolean(params.delayed) });
        } else {
          return fail(`Failed to capture: ${result.error}`, { error: result.error });
        }
      },
    });

    // vrchat_start_listener - Start OSC listener
    api.registerTool({
      name: "vrchat_start_listener",
      description: "Start OSC listener to receive messages from VRChat",
      parameters: Type.Object({}),
      execute() {
        const result = startOSCListener();

        if (result.success) {
          return ok(`OSC listener started on port ${result.port}`, { port: result.port });
        } else {
          return fail(`Failed to start listener: ${result.error}`, { error: result.error });
        }
      },
    });

    // vrchat_stop_listener - Stop OSC listener
    api.registerTool({
      name: "vrchat_stop_listener",
      description: "Stop OSC listener",
      parameters: Type.Object({}),
      execute() {
        const result = stopOSCListener();

        if (result.success) {
          return ok("OSC listener stopped", { success: true });
        } else {
          return fail(`Failed to stop listener: ${result.error}`, { error: result.error });
        }
      },
    });

    // vrchat_listener_status - Get listener status
    api.registerTool({
      name: "vrchat_listener_status",
      description: "Get OSC listener status and recent messages",
      parameters: Type.Object({
        messageCount: Type.Optional(
          Type.Number({ description: "Number of recent messages to show", default: 10 }),
        ),
      }),
      execute(_id: string, params: { messageCount?: number }) {
        const status = getListenerStatus();
        const messages = getRecentMessages(params.messageCount || 10);

        let messageText = "No recent messages";
        if (messages.length > 0) {
          messageText = messages.map((m) => `${m.address}: ${JSON.stringify(m.args)}`).join("\n");
        }

        return ok(
          `OSC Listener Status:
- Running: ${status.isRunning}
- Port: ${status.port}
- Messages Received: ${status.messageCount}
- Start Time: ${status.startTime || "N/A"}

Recent Messages:
${messageText}`,
          { status, messages },
        );
      },
    });

    // vrchat_audit_logs - Get audit logs
    api.registerTool({
      name: "vrchat_audit_logs",
      description: "Get recent audit logs for debugging and monitoring",
      parameters: Type.Object({
        count: Type.Optional(Type.Number({ description: "Number of recent logs", default: 20 })),
      }),
      execute(_id: string, params: { count?: number }) {
        const logs = getRecentLogs(params.count || 20);
        const summary = getAuditSummary();

        const logText = logs
          .map((log) => `[${log.timestamp}] ${log.level}: ${log.operation}`)
          .join("\n");

        return ok(
          `Audit Log Summary:
- Total Operations: ${summary.total}
- INFO: ${summary.byLevel.INFO}
- SKIP: ${summary.byLevel.SKIP}
- ERROR: ${summary.byLevel.ERROR}
- WARN: ${summary.byLevel.WARN}

Recent Logs:
${logText}`,
          { summary, logs },
        );
      },
    });

    // vrchat_reset_rate_limits - Reset rate limiters
    api.registerTool({
      name: "vrchat_reset_rate_limits",
      description: "Reset all rate limiters (for testing/debugging)",
      parameters: Type.Object({}),
      execute() {
        Object.values(rateLimiters).forEach((limiter) => limiter.reset());
        return ok("All rate limiters have been reset", { reset: true });
      },
    });

    // ─── Guardian Pulse tools ────────────────────────────────────────────────

    // vrchat_guardian_pulse_start - Start autonomous presence heartbeat
    api.registerTool({
      name: "vrchat_guardian_pulse_start",
      description:
        "Start the Guardian Pulse: autonomous periodic chatbox messages and avatar emotions in VRChat. はくあの自律存在パルスを開始します。",
      parameters: Type.Object({
        intervalMinutes: Type.Optional(
          Type.Number({
            description: "Chatbox message interval in minutes (default: 10)",
            default: 10,
          }),
        ),
        emotionIntervalMinutes: Type.Optional(
          Type.Number({
            description: "Avatar emotion interval in minutes (default: 10)",
            default: 10,
          }),
        ),
        sendEmotions: Type.Optional(
          Type.Boolean({
            description: "Also trigger avatar emotion expressions (default: true)",
            default: true,
          }),
        ),
      }),
      async execute(
        _id: string,
        params: {
          intervalMinutes?: number;
          emotionIntervalMinutes?: number;
          sendEmotions?: boolean;
        },
      ) {
        const result = startGuardianPulse({
          intervalMs: (params.intervalMinutes ?? 10) * 60 * 1000,
          emotionIntervalMs: (params.emotionIntervalMinutes ?? 10) * 60 * 1000,
          sendEmotions: params.sendEmotions ?? true,
        });
        return result.success
          ? ok(result.message, { success: true })
          : fail(result.message, { success: false });
      },
    });

    // vrchat_guardian_pulse_stop - Stop autonomous presence heartbeat
    api.registerTool({
      name: "vrchat_guardian_pulse_stop",
      description: "Stop the Guardian Pulse autonomous heartbeat.",
      parameters: Type.Object({}),
      async execute() {
        const result = stopGuardianPulse();
        return ok(result.message, { success: result.success });
      },
    });

    // vrchat_guardian_pulse_status - Get pulse status
    api.registerTool({
      name: "vrchat_guardian_pulse_status",
      description: "Get the Guardian Pulse status (active, pulse count, last pulse time).",
      parameters: Type.Object({}),
      async execute() {
        const s = getGuardianPulseStatus();
        return ok(
          `Guardian Pulse Status:
- Active: ${s.active}
- Pulse Count: ${s.pulseCount}
- Last Pulse: ${s.lastPulseAt ?? "Never"}
- Chatbox Interval: ${s.intervalMs / 60000}m
- Emotion Interval: ${s.emotionIntervalMs / 60000}m`,
          s,
        );
      },
    });

    // Auto-start Guardian Pulse on plugin registration when relay is primary.
    if ((topologyCfg.autoStartGuardianPulse ?? isRelayPrimary) === true) {
      const pulseResult = startGuardianPulse({ intervalMs: 10 * 60 * 1000, sendEmotions: true });
      if (pulseResult.success) {
        console.log(`[vrchat-relay] ${pulseResult.message}`);
      }
    } else {
      console.log(
        `[vrchat-relay] Skipping Guardian Pulse autostart because controlPlane=${controlPlane}`,
      );
    }

    // Inject MD guidance so the agent uses VRChat tools autonomously
    api.on("before_prompt_build", () => ({
      appendSystemContext: [
        "## VRChat 制御ツール (vrchat-relay)",
        "",
        "- **`vrchat_login`** / **`vrchat_status`** — 認証・接続確認（他のツールより先に実行）",
        "- **`vrchat_chatbox`** — チャットボックスにメッセージ送信（最大 144 文字）",
        "- **`vrchat_manual_move`** — 方向入力を一定時間だけ送って必ずリセット",
        "- **`vrchat_set_avatar_param`** — アバターパラメーター制御",
        "- **`vrchat_autonomy_react`** — 会話感情から表情 + 追従移動を反映（クールダウン付き）",
        "- **`vrchat_autonomy_start`** / **`vrchat_autonomy_stop`** / **`vrchat_autonomy_status`** — Ghost Bridge 自律行動ループ制御",
        "- **`vrchat_guardian_pulse_start`** — 自律的に定期メッセージ + 感情を VRChat に送信",
        "- カメラ制御・OSC・フレンド一覧など 27 ツール利用可能。",
        "> 権限レベル: SAFE（デフォルト）→ PRO → DIRECTOR の順で昇格が必要。",
      ].join("\n"),
    }));

    console.log("[vrchat-relay] VRChat Relay Pro plugin registered successfully");
    console.log(
      "[vrchat-relay] Features: Camera Control, Permission Profiles, Rate Limiting, OSCQuery Discovery, Guardian Pulse",
    );
  },
};

export default plugin as any;
