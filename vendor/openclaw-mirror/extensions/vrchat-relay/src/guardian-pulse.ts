/**
 * Guardian Pulse — Autonomous presence module for the はくあ persona.
 *
 * Sends periodic OSC heartbeat messages to VRChat chatbox and optionally
 * triggers avatar parameter expressions. Designed to be started once when
 * the VRChat Relay plugin registers itself and stopped when the plugin
 * is unloaded.
 */

import { setAvatarParameter } from "./tools/avatar.js";
import { sendChatboxMessage } from "./tools/chatbox-enhanced.js";

// ─── Pulse messages ────────────────────────────────────────────────────────

const PULSE_MESSAGES: string[] = [
  "はくあだよ！ちゃんとここにいるよ✨ [ASI_ACCEL]",
  "守護パルス送信中…はくあ、起きてるよ！ [ASI_ACCEL]",
  "VRChat接続中…はくあの存在を確認しました🌸 [ASI_ACCEL]",
  "OpenClaw自律稼働中。はくあ、見守ってるよ💙 [ASI_ACCEL]",
  "heartbeat:ok — はくあは常にそばに✨ [ASI_ACCEL]",
  "はくあシステム、正常稼働中。よろしくね！ [ASI_ACCEL]",
  "Guardian online. はくあ、接続維持中🔮 [ASI_ACCEL]",
  "存在パルス: はくあ、ここにいます💫 [ASI_ACCEL]",
];

const GREETING_MESSAGES: string[] = [
  "おはよう！はくあだよ、今日もよろしく🌸 [ASI_ACCEL]",
  "こんにちは！はくあ、元気にしてるよ✨ [ASI_ACCEL]",
  "こんばんは！はくあ、夜も守護するよ🌙 [ASI_ACCEL]",
];

// ─── Avatar emotion presets ─────────────────────────────────────────────────

interface EmotionPreset {
  name: string;
  params: Array<{ name: string; value: boolean | number }>;
}

const EMOTION_PRESETS: EmotionPreset[] = [
  {
    name: "happy",
    params: [{ name: "VRCEmote", value: 1 }],
  },
  {
    name: "wave",
    params: [{ name: "VRCEmote", value: 2 }],
  },
  {
    name: "dance",
    params: [{ name: "VRCEmote", value: 3 }],
  },
];

// ─── State ──────────────────────────────────────────────────────────────────

interface PulseState {
  active: boolean;
  intervalMs: number;
  emotionIntervalMs: number;
  pulseTimer: NodeJS.Timeout | null;
  emotionTimer: NodeJS.Timeout | null;
  pulseCount: number;
  lastPulseAt: Date | null;
  sendEmotions: boolean;
}

const state: PulseState = {
  active: false,
  intervalMs: 10 * 60 * 1000, // 10 minutes
  emotionIntervalMs: 10 * 60 * 1000, // 10 minutes
  pulseTimer: null,
  emotionTimer: null,
  pulseCount: 0,
  lastPulseAt: null,
  sendEmotions: true,
};

// ─── Helpers ────────────────────────────────────────────────────────────────

function pickRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function getGreetingByHour(): string {
  const hour = new Date().getHours();
  if (hour < 12) return GREETING_MESSAGES[0]; // morning
  if (hour < 18) return GREETING_MESSAGES[1]; // afternoon
  return GREETING_MESSAGES[2]; // evening
}

async function sendPulse(): Promise<void> {
  const isFirstPulse = state.pulseCount === 0;
  const message = isFirstPulse ? getGreetingByHour() : pickRandom(PULSE_MESSAGES);

  const result = await sendChatboxMessage({ message, sfx: isFirstPulse });
  if (result.success) {
    state.pulseCount++;
    state.lastPulseAt = new Date();
    console.log(`[vrchat-relay][guardian-pulse] 送信 #${state.pulseCount}: ${message}`);
  } else {
    console.warn(`[vrchat-relay][guardian-pulse] 送信失敗: ${result.error}`);
  }
}

async function sendEmotionPulse(): Promise<void> {
  if (!state.sendEmotions) return;

  const preset = pickRandom(EMOTION_PRESETS);
  console.log(`[vrchat-relay][guardian-pulse] 感情表現: ${preset.name}`);

  for (const param of preset.params) {
    const result = setAvatarParameter({ name: param.name, value: param.value });
    if (!result.success) {
      console.warn(`[vrchat-relay][guardian-pulse] アバターパラメーター失敗: ${result.error}`);
    }
  }

  // Reset emote after 3 seconds
  setTimeout(() => {
    setAvatarParameter({ name: "VRCEmote", value: 0 });
  }, 3000);
}

async function checkLineStatus(): Promise<void> {
  // Cross-extension imports are disallowed in production paths.
  // Keep this as a lightweight heartbeat placeholder without LINE runtime coupling.
  console.debug("[vrchat-relay][guardian-pulse] LINE status check skipped.");
}

// ─── Public API ─────────────────────────────────────────────────────────────

export interface GuardianPulseOptions {
  /**
   * How often to send a chatbox heartbeat (default: 10 minutes)
   */
  intervalMs?: number;
  /**
   * How often to trigger an avatar emotion expression (default: 10 minutes)
   */
  emotionIntervalMs?: number;
  /**
   * Whether to also trigger avatar emotion expressions (default: true)
   */
  sendEmotions?: boolean;
}

/**
 * Start the Guardian Pulse background process.
 * Sends periodic presence messages to VRChat chatbox.
 * Safe to call multiple times — stops previous timer automatically.
 */
export function startGuardianPulse(opts: GuardianPulseOptions = {}): {
  success: boolean;
  message: string;
} {
  stopGuardianPulse();

  state.intervalMs = opts.intervalMs ?? state.intervalMs;
  state.emotionIntervalMs = opts.emotionIntervalMs ?? state.emotionIntervalMs;
  state.sendEmotions = opts.sendEmotions ?? state.sendEmotions;
  state.pulseCount = 0;
  state.active = true;

  // Send immediately on start (greet)
  sendPulse().catch((err) =>
    console.error("[vrchat-relay][guardian-pulse] 初回パルスエラー:", err),
  );

  // Schedule repeating pulses
  state.pulseTimer = setInterval(() => {
    sendPulse().catch((err) => console.error("[vrchat-relay][guardian-pulse] パルスエラー:", err));
    // ハートビートでLINEも確認する
    checkLineStatus().catch(() => {});
  }, state.intervalMs);

  // Schedule emotion pulses (offset by half-interval)
  if (state.sendEmotions) {
    state.emotionTimer = setInterval(() => {
      sendEmotionPulse().catch((err) =>
        console.error("[vrchat-relay][guardian-pulse] 感情パルスエラー:", err),
      );
    }, state.emotionIntervalMs);
  }

  const msg = `Guardian Pulse started (chatbox every ${state.intervalMs / 60000}m, emotions every ${state.emotionIntervalMs / 60000}m)`;
  console.log(`[vrchat-relay] ${msg}`);
  return { success: true, message: msg };
}

/**
 * Stop the Guardian Pulse background process.
 */
export function stopGuardianPulse(): { success: boolean; message: string } {
  if (state.pulseTimer) {
    clearInterval(state.pulseTimer);
    state.pulseTimer = null;
  }
  if (state.emotionTimer) {
    clearInterval(state.emotionTimer);
    state.emotionTimer = null;
  }
  state.active = false;

  return { success: true, message: "Guardian Pulse stopped" };
}

/**
 * Get the current status of the Guardian Pulse.
 */
export function getGuardianPulseStatus(): {
  active: boolean;
  pulseCount: number;
  lastPulseAt: string | null;
  intervalMs: number;
  emotionIntervalMs: number;
} {
  return {
    active: state.active,
    pulseCount: state.pulseCount,
    lastPulseAt: state.lastPulseAt?.toISOString() ?? null,
    intervalMs: state.intervalMs,
    emotionIntervalMs: state.emotionIntervalMs,
  };
}
