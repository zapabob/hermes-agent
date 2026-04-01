/**
 * Hypura Python harness — HTTP proxy tools for the FastAPI daemon (scripts/hypura/harness_daemon.py).
 * Default base URL matches harness.config.json (port 18794; avoids OpenClaw Bridge on 18790).
 */
import { Type } from "@sinclair/typebox";
import { stringEnum } from "openclaw/plugin-sdk/core";
import { definePluginEntry, type OpenClawPluginApi } from "openclaw/plugin-sdk/plugin-entry";

const DEFAULT_BASE_URL = "http://127.0.0.1:18794";

type HarnessPluginConfig = {
  baseUrl?: string;
};

function resolveBaseUrl(api: OpenClawPluginApi): string {
  const cfg = (api.pluginConfig ?? {}) as HarnessPluginConfig;
  const raw = typeof cfg.baseUrl === "string" ? cfg.baseUrl.trim() : "";
  return raw || DEFAULT_BASE_URL;
}

function okText(text: string, details: Record<string, unknown> = {}) {
  return {
    content: [{ type: "text" as const, text }],
    details,
  };
}

async function harnessJson(
  api: OpenClawPluginApi,
  path: string,
  init?: RequestInit,
  timeoutMs = 120_000,
): Promise<unknown> {
  const base = resolveBaseUrl(api);
  const url = `${base.replace(/\/$/, "")}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(
      `Hypura harness unreachable at ${base}. Start: cd scripts/hypura && uv run harness_daemon.py (${msg})`,
    );
  }
  const text = await res.text();
  let body: unknown;
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = { raw: text };
  }
  if (!res.ok) {
    const errObj = body as { detail?: string };
    const detail = typeof errObj?.detail === "string" ? errObj.detail : text;
    throw new Error(`Hypura harness HTTP ${res.status}: ${detail}`);
  }
  return body;
}

export default definePluginEntry({
  id: "hypura-harness",
  name: "Hypura Harness",
  description:
    "Call the Hypura Python harness HTTP API (OSC, VOICEVOX, code run, skills, evolve, LoRA jobs).",
  register(api: OpenClawPluginApi) {
    api.registerTool({
      name: "hypura_harness_status",
      label: "Hypura Harness Status",
      description: "GET /status — voicevox, ollama, LoRA summary and daemon health.",
      parameters: Type.Object({}),
      async execute() {
        const data = (await harnessJson(api, "/status", undefined, 10_000)) as Record<
          string,
          unknown
        >;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    api.registerTool({
      name: "hypura_harness_osc",
      label: "Hypura Harness OSC",
      description:
        "POST /osc — VRChat OSC: chatbox, emotion, param, move/jump/move_forward/turn_* (see Hypura harness docs).",
      parameters: Type.Object({
        action: Type.String({ description: "e.g. chatbox, emotion, param, jump, move_forward" }),
        payload: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
      }),
      async execute(_id: string, params: Record<string, unknown>) {
        const action = typeof params.action === "string" ? params.action : "";
        const payload =
          params.payload && typeof params.payload === "object" && params.payload !== null
            ? (params.payload as Record<string, unknown>)
            : {};
        const data = (await harnessJson(api, "/osc", {
          method: "POST",
          body: JSON.stringify({ action, payload }),
        })) as Record<string, unknown>;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    api.registerTool({
      name: "hypura_harness_speak",
      label: "Hypura Harness Speak",
      description: "POST /speak — VOICEVOX speech (text or scene array).",
      parameters: Type.Object({
        text: Type.Optional(Type.String()),
        emotion: Type.Optional(Type.String()),
        speaker: Type.Optional(Type.Number()),
        scene: Type.Optional(Type.Array(Type.Unknown())),
      }),
      async execute(_id: string, params: Record<string, unknown>) {
        const body: Record<string, unknown> = {};
        if (typeof params.text === "string") {
          body.text = params.text;
        }
        if (typeof params.emotion === "string") {
          body.emotion = params.emotion;
        }
        if (typeof params.speaker === "number" && Number.isFinite(params.speaker)) {
          body.speaker = params.speaker;
        }
        if (Array.isArray(params.scene)) {
          body.scene = params.scene;
        }
        const data = (await harnessJson(api, "/speak", {
          method: "POST",
          body: JSON.stringify(body),
        })) as Record<string, unknown>;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    api.registerTool({
      name: "hypura_harness_run",
      label: "Hypura Harness Run",
      description:
        "POST /run — generate and execute Python via harness code_runner (PEP 723 + uv).",
      parameters: Type.Object({
        task: Type.String({ description: "Natural language task for code generation." }),
        model: Type.Optional(Type.String()),
        max_retries: Type.Optional(Type.Number()),
      }),
      async execute(_id: string, params: Record<string, unknown>) {
        const task = typeof params.task === "string" ? params.task : "";
        const body: Record<string, unknown> = { task };
        if (typeof params.model === "string") {
          body.model = params.model;
        }
        if (typeof params.max_retries === "number" && Number.isFinite(params.max_retries)) {
          body.max_retries = params.max_retries;
        }
        const data = (await harnessJson(api, "/run", {
          method: "POST",
          body: JSON.stringify(body),
        })) as Record<string, unknown>;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    api.registerTool({
      name: "hypura_harness_skill",
      label: "Hypura Harness Skill",
      description: "POST /skill — generate a new workspace skill (SKILL.md) via harness.",
      parameters: Type.Object({
        name: Type.String(),
        description: Type.String(),
        examples: Type.Optional(Type.Array(Type.String())),
      }),
      async execute(_id: string, params: Record<string, unknown>) {
        const body = {
          name: typeof params.name === "string" ? params.name : "",
          description: typeof params.description === "string" ? params.description : "",
          examples: Array.isArray(params.examples)
            ? params.examples.filter((x) => typeof x === "string")
            : [],
        };
        const data = (await harnessJson(api, "/skill", {
          method: "POST",
          body: JSON.stringify(body),
        })) as Record<string, unknown>;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    api.registerTool({
      name: "hypura_harness_evolve",
      label: "Hypura Harness Evolve",
      description: "POST /evolve — ShinkaEvolve loop for code or skill targets.",
      parameters: Type.Object({
        target: stringEnum(["code", "skill"] as const, { description: "Evolution target" }),
        seed: Type.String({ description: "Starting code or skill text." }),
        fitness_hint: Type.Optional(Type.String()),
        generations: Type.Optional(Type.Number()),
      }),
      async execute(_id: string, params: Record<string, unknown>) {
        const body: Record<string, unknown> = {
          target: params.target,
          seed: typeof params.seed === "string" ? params.seed : "",
        };
        if (typeof params.fitness_hint === "string") {
          body.fitness_hint = params.fitness_hint;
        }
        if (typeof params.generations === "number" && Number.isFinite(params.generations)) {
          body.generations = params.generations;
        }
        const data = (await harnessJson(api, "/evolve", {
          method: "POST",
          body: JSON.stringify(body),
        })) as Record<string, unknown>;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    api.registerTool({
      name: "hypura_harness_lora_status",
      label: "Hypura Harness LoRA Status",
      description: "GET /lora/status — LoRA paths and environment resolution summary.",
      parameters: Type.Object({}),
      async execute() {
        const data = (await harnessJson(api, "/lora/status", undefined, 15_000)) as Record<
          string,
          unknown
        >;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    api.registerTool({
      name: "hypura_harness_lora_curriculum_build",
      label: "Hypura Harness LoRA Curriculum Build",
      description: "POST /lora/curriculum/build — enqueue curriculum JSONL build job.",
      parameters: Type.Object({
        arxiv_ids: Type.Optional(Type.Array(Type.String())),
        include_soul: Type.Optional(Type.Boolean()),
        extra_jsonl: Type.Optional(Type.Array(Type.String())),
      }),
      async execute(_id: string, params: Record<string, unknown>) {
        const body: Record<string, unknown> = {};
        if (Array.isArray(params.arxiv_ids)) {
          body.arxiv_ids = params.arxiv_ids.filter((x) => typeof x === "string");
        }
        if (typeof params.include_soul === "boolean") {
          body.include_soul = params.include_soul;
        }
        if (Array.isArray(params.extra_jsonl)) {
          body.extra_jsonl = params.extra_jsonl.filter((x) => typeof x === "string");
        }
        const data = (await harnessJson(api, "/lora/curriculum/build", {
          method: "POST",
          body: JSON.stringify(body),
        })) as Record<string, unknown>;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    api.registerTool({
      name: "hypura_harness_lora_train",
      label: "Hypura Harness LoRA Train",
      description: "POST /lora/train — enqueue LoRA SFT train job (dry_run recommended first).",
      parameters: Type.Object({
        dry_run: Type.Optional(Type.Boolean()),
        dataset_path: Type.Optional(Type.String()),
      }),
      async execute(_id: string, params: Record<string, unknown>) {
        const body: Record<string, unknown> = {};
        if (typeof params.dry_run === "boolean") {
          body.dry_run = params.dry_run;
        }
        if (typeof params.dataset_path === "string") {
          body.dataset_path = params.dataset_path;
        }
        const data = (await harnessJson(api, "/lora/train", {
          method: "POST",
          body: JSON.stringify(body),
        })) as Record<string, unknown>;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    api.registerTool({
      name: "hypura_harness_lora_grpo",
      label: "Hypura Harness LoRA GRPO",
      description: "POST /lora/grpo — GRPO placeholder or train job (mode placeholder|train).",
      parameters: Type.Object({
        mode: Type.Optional(
          stringEnum(["placeholder", "train"] as const, { description: "GRPO mode" }),
        ),
        dataset_path: Type.Optional(Type.String()),
      }),
      async execute(_id: string, params: Record<string, unknown>) {
        const body: Record<string, unknown> = {};
        if (params.mode === "placeholder" || params.mode === "train") {
          body.mode = params.mode;
        }
        if (typeof params.dataset_path === "string") {
          body.dataset_path = params.dataset_path;
        }
        const data = (await harnessJson(api, "/lora/grpo", {
          method: "POST",
          body: JSON.stringify(body),
        })) as Record<string, unknown>;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    api.registerTool({
      name: "hypura_harness_lora_job",
      label: "Hypura Harness LoRA Job",
      description: "GET /lora/jobs/{job_id} — poll async LoRA job status.",
      parameters: Type.Object({
        job_id: Type.String(),
      }),
      async execute(_id: string, params: Record<string, unknown>) {
        const jobId = typeof params.job_id === "string" ? encodeURIComponent(params.job_id) : "";
        const data = (await harnessJson(api, `/lora/jobs/${jobId}`, undefined, 15_000)) as Record<
          string,
          unknown
        >;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    // ── 継続改善ループ ────────────────────────────────────────────────────────

    api.registerTool({
      name: "hypura_loop_status",
      label: "Hypura Loop Status",
      description:
        "GET /status — Redis ループ状態を確認する。training:examples / atlas:failures / TinyLoRA adapter 状況を返す。",
      parameters: Type.Object({}),
      async execute() {
        const data = (await harnessJson(api, "/status", undefined, 10_000)) as Record<
          string,
          unknown
        >;
        const loop = (data.loop ?? {}) as Record<string, unknown>;
        const summary = [
          `Redis: ${loop.redis ?? "unknown"}`,
          `training:examples = ${loop.training_examples ?? "?"}`,
          `atlas:failures = ${loop.failures ?? "?"}`,
          `shinka:fitness_hints = ${loop.fitness_hints ?? "?"}`,
          `TinyLoRA adapter ready: ${loop.tinylora_adapter_ready ?? false}`,
          `Training in progress: ${loop.training_in_progress ?? false}`,
          loop.last_trained ? `Last trained: ${loop.last_trained}` : "Never trained",
        ].join("\n");
        return okText(summary, { loop });
      },
    });

    api.registerTool({
      name: "hypura_tinylora_train",
      label: "Hypura TinyLoRA Train",
      description:
        "POST /lora/train — TinyLoRA (arXiv:2602.04118) で qwen-hakua-core2 を学習する。" +
        "13 パラメータで秒〜分単位の高速学習。mode=tinylora|sft|auto を選択できる。",
      parameters: Type.Object({
        mode: Type.Optional(stringEnum(["auto", "tinylora", "sft"] as const, { default: "auto" })),
        dry_run: Type.Optional(Type.Boolean()),
        dataset_path: Type.Optional(Type.String()),
      }),
      async execute(_id: string, params: Record<string, unknown>) {
        const body: Record<string, unknown> = {
          mode: params.mode ?? "auto",
          dry_run: params.dry_run ?? true,
        };
        if (typeof params.dataset_path === "string") {
          body.dataset_path = params.dataset_path;
        }
        const data = (await harnessJson(
          api,
          "/lora/train",
          {
            method: "POST",
            body: JSON.stringify(body),
          },
          600_000,
        )) as Record<string, unknown>;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    // ── AI Scientist ──────────────────────────────────────────────────────

    api.registerTool({
      name: "hypura_scientist_run",
      label: "Hypura AI Scientist Run",
      description:
        "POST /scientist/run — AI-Scientist (SakanaAI, Ollama モード) でリサーチアイデアを生成して Redis に保存する。" +
        "topic が空なら atlas:failures から自動設定。run_experiment=true で実験実行まで行う。",
      parameters: Type.Object({
        topic: Type.Optional(
          Type.String({ description: "研究テーマ (空=atlas:failuresから自動設定)" }),
        ),
        num_ideas: Type.Optional(Type.Number({ default: 3, description: "生成するアイデア数" })),
        run_experiment: Type.Optional(
          Type.Boolean({ default: false, description: "実験実行も行う" }),
        ),
        model: Type.Optional(Type.String({ default: "ollama/qwen-Hakua-core2" })),
      }),
      async execute(_id: string, params: Record<string, unknown>) {
        const body: Record<string, unknown> = {
          topic: params.topic ?? "",
          num_ideas: params.num_ideas ?? 3,
          run_experiment: params.run_experiment ?? false,
          model: params.model ?? "ollama/qwen-Hakua-core2",
        };
        const data = (await harnessJson(
          api,
          "/scientist/run",
          {
            method: "POST",
            body: JSON.stringify(body),
          },
          300_000,
        )) as Record<string, unknown>;
        return okText(JSON.stringify(data, null, 2), data);
      },
    });

    api.registerTool({
      name: "hypura_scientist_ideas",
      label: "Hypura AI Scientist Ideas",
      description:
        "POST /scientist/ideas — AI-Scientist でアイデア一覧のみ生成して返す (Redis 保存なし)。" +
        "Ollama の qwen-Hakua-core2 を使用。",
      parameters: Type.Object({
        topic: Type.Optional(Type.String({ description: "研究テーマ" })),
        num_ideas: Type.Optional(Type.Number({ default: 3 })),
        model: Type.Optional(Type.String({ default: "ollama/qwen-Hakua-core2" })),
      }),
      async execute(_id: string, params: Record<string, unknown>) {
        const body: Record<string, unknown> = {
          topic: params.topic ?? "",
          num_ideas: params.num_ideas ?? 3,
          model: params.model ?? "ollama/qwen-Hakua-core2",
        };
        const data = (await harnessJson(
          api,
          "/scientist/ideas",
          {
            method: "POST",
            body: JSON.stringify(body),
          },
          120_000,
        )) as Record<string, unknown>;
        const ideas = (data.ideas as unknown[]) ?? [];
        const summary = ideas
          .map((idea: unknown, i: number) => {
            const obj = idea as Record<string, unknown>;
            return `[${i + 1}] ${obj.Name ?? obj.Title ?? "idea"}: ${obj.fitness_hint ?? ""}`;
          })
          .join("\n");
        return okText(summary || JSON.stringify(data, null, 2), data);
      },
    });

    api.registerTool({
      name: "hypura_scientist_status",
      label: "Hypura AI Scientist Status",
      description:
        "GET /scientist/status — ai_scientist:findings / ai_scientist:tasks のキュー状態を確認する。",
      parameters: Type.Object({}),
      async execute() {
        const data = (await harnessJson(api, "/scientist/status", undefined, 10_000)) as Record<
          string,
          unknown
        >;
        const summary = [
          `Findings stored: ${data.findings ?? "?"}`,
          `Tasks queued:    ${data.tasks ?? "?"}`,
          `Redis:           ${data.redis ?? "unknown"}`,
        ].join("\n");
        return okText(summary, data);
      },
    });

    api.on("before_prompt_build", () => ({
      appendSystemContext: [
        "## Hypura Python harness (hypura-harness plugin)",
        "",
        "- Prefer **`hypura_harness_status`** before other harness tools.",
        "- VRChat / VOICEVOX: **`hypura_harness_osc`**, **`hypura_harness_speak`**.",
        "- Code execution: **`hypura_harness_run`** (→ 成功時に training:examples へ保存、失敗時に ShinkaEvolve → atlas:failures へ記録).",
        "- Skills / evolution / LoRA: **`hypura_harness_skill`**, **`hypura_harness_evolve`**, `hypura_harness_lora_*`.",
        "- Loop monitoring: **`hypura_loop_status`** で training:examples / failures / TinyLoRA adapter 状況を確認.",
        "- TinyLoRA training: **`hypura_tinylora_train`** (qwen-hakua-core2 を 13 params で学習; mode=auto/tinylora/sft).",
        "- AI Scientist: **`hypura_scientist_run`** (SakanaAI/AI-Scientist, Ollama モード; アイデア生成→Redis保存), **`hypura_scientist_ideas`** (アイデアのみ取得), **`hypura_scientist_status`** (findings/tasks キュー確認).",
        `- Default URL: ${DEFAULT_BASE_URL} (override via plugins.entries["hypura-harness"].config.baseUrl).`,
        "- If tools fail to connect: `cd scripts/hypura && uv run harness_daemon.py`",
      ].join("\n"),
    }));
  },
});
