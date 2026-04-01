import { describe, expect, it, vi } from "vitest";
import plugin from "./index.js";

describe("hypura-harness plugin", () => {
  it("registers tools and wires status to fetch", async () => {
    const tools: Array<{
      name: string;
      execute: (id: string, p: Record<string, unknown>) => Promise<unknown>;
    }> = [];
    const onHandlers: Record<string, () => unknown> = {};
    const mockApi = {
      pluginConfig: { baseUrl: "http://127.0.0.1:18794" },
      config: {},
      registerTool(t: {
        name: string;
        execute: (id: string, p: Record<string, unknown>) => Promise<unknown>;
      }) {
        tools.push(t);
      },
      on: vi.fn((event: string, fn: () => unknown) => {
        onHandlers[event] = fn;
      }),
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ daemon_version: "0.1.0" }),
    });

    plugin.register(mockApi as never);

    expect(tools.some((t) => t.name === "hypura_harness_status")).toBe(true);
    expect(tools.some((t) => t.name === "hypura_harness_osc")).toBe(true);
    expect(mockApi.on).toHaveBeenCalledWith("before_prompt_build", expect.any(Function));

    const statusTool = tools.find((t) => t.name === "hypura_harness_status")!;
    const res = (await statusTool.execute("id", {})) as {
      content: Array<{ type: string; text: string }>;
    };
    expect(res.content[0].text).toContain("daemon_version");
    expect(global.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:18794/status",
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );

    const ctx = onHandlers.before_prompt_build?.() as { appendSystemContext?: string };
    expect(ctx?.appendSystemContext).toContain("hypura_harness_status");
  });
});
