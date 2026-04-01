import {
  definePluginEntry,
  type OpenClawPluginApi,
  type ProviderAuthContext,
  type ProviderAuthMethodNonInteractiveContext,
  type ProviderAuthResult,
  type ProviderDiscoveryContext,
} from "openclaw/plugin-sdk/core";
import { resolveOllamaApiBase } from "openclaw/plugin-sdk/ollama-surface";

const PROVIDER_ID = "hypura";
const DEFAULT_BASE_URL = "http://127.0.0.1:8080";
const DEFAULT_API_KEY = "hypura-local";

/** Hypura serves an Ollama-compatible API at http://127.0.0.1:8080 by default.
 *  Start with: hypura serve --model ./model.gguf [--port 8080]
 */
export default definePluginEntry({
  id: "hypura",
  name: "Hypura Provider",
  description: "Storage-tier-aware local LLM inference via hypura serve (Ollama-compatible API)",
  register(api: OpenClawPluginApi) {
    const apiAny = api as any;
    apiAny.registerProvider({
      id: PROVIDER_ID,
      label: "Hypura",
      docsPath: "/providers/hypura",
      envVars: ["HYPURA_API_KEY"],
      auth: [
        {
          id: "local",
          label: "Hypura",
          hint: "Local LLM with NVMe tiered scheduling (hypura serve)",
          kind: "custom",
          run: async (ctx: ProviderAuthContext): Promise<ProviderAuthResult> => {
            // Attempt to discover a running hypura server
            const baseUrl = ctx.config.models?.providers?.hypura?.baseUrl ?? DEFAULT_BASE_URL;

            const prompterAny = ctx.prompter as any;
            await prompterAny.print?.(
              `Connecting to Hypura server at ${baseUrl}\n` +
                `Make sure it is running: hypura serve --model ./model.gguf\n`,
            );

            return {
              profiles: [
                {
                  profileId: "hypura:default",
                  credential: {
                    type: "api_key",
                    provider: PROVIDER_ID,
                    key: DEFAULT_API_KEY,
                  },
                },
              ],
              configPatch: {},
            };
          },
          runNonInteractive: async (_ctx: ProviderAuthMethodNonInteractiveContext) => {
            return {
              profiles: [
                {
                  profileId: "hypura:default",
                  credential: {
                    type: "api_key",
                    provider: PROVIDER_ID,
                    key: DEFAULT_API_KEY,
                  },
                },
              ],
              configPatch: {},
            } as any;
          },
        },
      ],
      discovery: {
        order: "late",
        run: async (ctx: ProviderDiscoveryContext) => {
          const explicit = ctx.config.models?.providers?.hypura;
          const hasExplicitModels = Array.isArray(explicit?.models) && explicit.models.length > 0;
          const hypuraKey = ctx.resolveProviderApiKey(PROVIDER_ID).apiKey ?? DEFAULT_API_KEY;

          if (hasExplicitModels && explicit) {
            return {
              provider: {
                ...explicit,
                baseUrl:
                  typeof explicit.baseUrl === "string" && explicit.baseUrl.trim()
                    ? resolveOllamaApiBase(explicit.baseUrl)
                    : DEFAULT_BASE_URL,
                api: "ollama" as const,
                apiKey: hypuraKey,
              },
            };
          }

          // Auto-discover: probe the default hypura serve port
          try {
            const probeUrl = `${DEFAULT_BASE_URL}/`;
            const res = await fetch(probeUrl, {
              signal: AbortSignal.timeout(1500),
            });
            if (!res.ok) return null;

            // Fetch available model from /api/tags
            const tagsRes = await fetch(`${DEFAULT_BASE_URL}/api/tags`, {
              signal: AbortSignal.timeout(1500),
            });
            if (!tagsRes.ok) return null;

            const tags = (await tagsRes.json()) as { models?: { name: string }[] };
            const models = (tags.models ?? []).map((m) => m.name);
            if (models.length === 0) return null;

            return {
              provider: {
                id: PROVIDER_ID,
                baseUrl: DEFAULT_BASE_URL,
                api: "ollama" as const,
                apiKey: hypuraKey,
                models: models.map((name) => ({ id: name })),
              },
            } as any;
          } catch {
            // hypura serve not running — skip silently
            return null;
          }
        },
      },
    });
  },
});
