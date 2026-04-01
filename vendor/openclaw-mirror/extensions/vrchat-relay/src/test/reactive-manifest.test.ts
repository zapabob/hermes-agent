import { beforeEach, describe, expect, it, vi } from "vitest";

const setAvatarParameter = vi.fn(() => ({ success: true }));
const performMovementWithReset = vi.fn(async () => ({ success: true }));

vi.mock("../tools/avatar.js", () => ({
  setAvatarParameter,
}));

vi.mock("../tools/input.js", () => ({
  performMovementWithReset,
}));

vi.mock("../tools/audit.js", () => ({
  logInfo: vi.fn(),
  logWarn: vi.fn(),
}));

describe("applyReactiveManifest", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("maps joyful text to smile parameter", async () => {
    const mod = await import("../autonomy/reactive-manifest.js");
    const result = await mod.applyReactiveManifest({
      text: "今日はめっちゃ嬉しい！",
      allowMovement: false,
    });

    expect(result.emotion).toBe("joy");
    expect(setAvatarParameter).toHaveBeenCalledWith({ name: "FX_Smile", value: true });
    expect(performMovementWithReset).not.toHaveBeenCalled();
  });

  it("triggers forward movement when follow intent exists", async () => {
    const mod = await import("../autonomy/reactive-manifest.js");
    const result = await mod.applyReactiveManifest({
      text: "こっちに来て",
      allowMovement: true,
    });

    expect(result.movementTriggered).toBe(true);
    expect(performMovementWithReset).toHaveBeenCalled();
  });
});
