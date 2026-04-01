import { logInfo, logWarn } from "../tools/audit.js";
import { setAvatarParameter } from "../tools/avatar.js";
import { performMovementWithReset } from "../tools/input.js";

type EmotionKey = "neutral" | "joy" | "love" | "angry" | "sad" | "surprised";

interface EmotionRule {
  key: EmotionKey;
  keywords: readonly string[];
  params: Array<{ name: string; value: boolean | number }>;
  resetAfterMs?: number;
}

export interface ReactiveManifestOptions {
  text: string;
  allowMovement?: boolean;
}

export interface ReactiveManifestResult {
  emotion: EmotionKey;
  movementTriggered: boolean;
  reason: string;
}

const EMOTION_COOLDOWN_MS = 1800;
const MOVEMENT_COOLDOWN_MS = 4500;
const FOLLOW_KEYWORDS = ["こっちに来", "ついてき", "follow", "come here", "近くに来"];

const EMOTION_RULES: readonly EmotionRule[] = [
  {
    key: "joy",
    keywords: ["嬉しい", "うれしい", "楽しい", "最高", "happy", "lol", "www"],
    params: [{ name: "FX_Smile", value: true }],
    resetAfterMs: 1800,
  },
  {
    key: "love",
    keywords: ["好き", "愛", "だいすき", "love", "かわいい"],
    params: [{ name: "FX_Love", value: true }],
    resetAfterMs: 2000,
  },
  {
    key: "angry",
    keywords: ["怒", "イラ", "むかつ", "angry", "annoyed"],
    params: [{ name: "FX_Angry", value: true }],
    resetAfterMs: 1600,
  },
  {
    key: "sad",
    keywords: ["悲しい", "つらい", "泣", "sad", "lonely"],
    params: [{ name: "FX_Sad", value: true }],
    resetAfterMs: 1700,
  },
  {
    key: "surprised",
    keywords: ["えっ", "まじ", "びっくり", "surprise", "what"],
    params: [{ name: "FX_Surprised", value: true }],
    resetAfterMs: 1200,
  },
];

const state = {
  lastEmotionAt: 0,
  lastMovementAt: 0,
};

function normalize(input: string): string {
  return input.toLowerCase();
}

function detectEmotion(input: string): EmotionRule | null {
  const normalized = normalize(input);
  for (const rule of EMOTION_RULES) {
    if (rule.keywords.some((keyword) => normalized.includes(keyword.toLowerCase()))) {
      return rule;
    }
  }
  return null;
}

function detectFollowIntent(input: string): boolean {
  const normalized = normalize(input);
  return FOLLOW_KEYWORDS.some((keyword) => normalized.includes(keyword.toLowerCase()));
}

function clearExpressionFlags(except: string): void {
  const candidates = ["FX_Smile", "FX_Love", "FX_Angry", "FX_Sad", "FX_Surprised"];
  for (const name of candidates) {
    if (name === except) continue;
    setAvatarParameter({ name, value: false });
  }
}

function triggerEmotion(rule: EmotionRule): void {
  clearExpressionFlags(rule.params[0]?.name ?? "");
  for (const param of rule.params) {
    setAvatarParameter({ name: param.name, value: param.value });
  }

  if (rule.resetAfterMs && rule.params.length > 0) {
    setTimeout(() => {
      for (const param of rule.params) {
        if (typeof param.value === "boolean") {
          setAvatarParameter({ name: param.name, value: false });
        }
      }
    }, rule.resetAfterMs);
  }
}

async function triggerFollowMovement(): Promise<boolean> {
  const result = await performMovementWithReset({ direction: "forward", durationMs: 900 });
  return result.success;
}

export async function applyReactiveManifest(
  options: ReactiveManifestOptions,
): Promise<ReactiveManifestResult> {
  const input = options.text.trim();
  const now = Date.now();
  let emotion: EmotionKey = "neutral";
  let movementTriggered = false;
  const reasons: string[] = [];

  const emotionRule = detectEmotion(input);
  if (emotionRule) {
    if (now - state.lastEmotionAt >= EMOTION_COOLDOWN_MS) {
      triggerEmotion(emotionRule);
      state.lastEmotionAt = now;
      emotion = emotionRule.key;
      reasons.push(`emotion:${emotionRule.key}`);
    } else {
      reasons.push("emotion:cooldown");
      logWarn("vrchat.autonomy.cooldown", { type: "emotion", cooldownMs: EMOTION_COOLDOWN_MS });
    }
  } else {
    setAvatarParameter({ name: "FX_Smile", value: false });
    setAvatarParameter({ name: "FX_Love", value: false });
    setAvatarParameter({ name: "FX_Angry", value: false });
    setAvatarParameter({ name: "FX_Sad", value: false });
    setAvatarParameter({ name: "FX_Surprised", value: false });
    reasons.push("emotion:neutral");
  }

  const wantsFollow = options.allowMovement === true && detectFollowIntent(input);
  if (wantsFollow) {
    if (now - state.lastMovementAt >= MOVEMENT_COOLDOWN_MS) {
      movementTriggered = await triggerFollowMovement();
      state.lastMovementAt = now;
      reasons.push(movementTriggered ? "movement:forward" : "movement:failed");
    } else {
      reasons.push("movement:cooldown");
      logWarn("vrchat.autonomy.cooldown", { type: "movement", cooldownMs: MOVEMENT_COOLDOWN_MS });
    }
  } else if (options.allowMovement) {
    reasons.push("movement:no-intent");
  }

  logInfo("vrchat.autonomy.reactive_manifest", {
    emotion,
    movementTriggered,
    reason: reasons.join(","),
  });

  return {
    emotion,
    movementTriggered,
    reason: reasons.join(","),
  };
}
