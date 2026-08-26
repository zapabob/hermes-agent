# Upstream snapshot integration, 2026-08-26

This report freezes the integration input. Commits newer than the recorded
upstream SHA are outside this campaign and must not be substituted.

## Snapshot

| Field | Value |
| --- | --- |
| Captured at | 2026-08-26T18:25:00+09:00 |
| Upstream head | 1fe0f2f3ac9748ce799272eb93bee2937b5ab802 |
| Downstream start | 88f659b4ef5a27dbf038fe9c6bf35b3967a277d8 |
| Merge base | ddbd928ee4e881f0c7b3536a00355647c6559fe2 |
| Delta commits | 329 |
| Upstream-touched files | 559 |
| Fork intersections | 113 |

## Decision counts

| Decision | Commits |
| --- | ---: |
| ADOPT | 100 |
| COMPOSE | 194 |
| DEFER | 15 |
| IGNORE | 20 |
| KEEP_DOWNSTREAM | 0 |
| REPLACE_DOWNSTREAM | 0 |

## Category counts

| Category | Commits |
| --- | ---: |
| BUGFIX_RELEVANT | 206 |
| CREDENTIAL_BOUNDARY | 16 |
| DATA_INTEGRITY | 24 |
| DESKTOP_API_CHANGE | 144 |
| DOCS_ONLY | 22 |
| FEATURE_NEW_RELEVANT | 33 |
| FEATURE_OVERLAP | 194 |
| GATEWAY_API_CHANGE | 22 |
| MODEL_PROVIDER_CHANGE | 30 |
| PLATFORM_IRRELEVANT | 1 |
| PLUGIN_API_CHANGE | 40 |
| PUBLIC_API_CHANGE | 32 |
| SECURITY_CRITICAL | 21 |
| TEST_INFRA | 41 |
| WINDOWS_RELEVANT | 14 |

## Direct fork intersections

- agent/agent_init.py
- agent/agent_runtime_helpers.py
- agent/auxiliary_client.py
- agent/chat_completion_helpers.py
- agent/context_compressor.py
- agent/memory_manager.py
- agent/prompt_builder.py
- agent/system_prompt.py
- agent/tool_executor.py
- agent/tool_guardrails.py
- apps/desktop/electron/connection-config.ts
- apps/desktop/electron/main.ts
- apps/desktop/electron/preload.ts
- apps/desktop/electron/primary-backend-startup.test.ts
- apps/desktop/electron/primary-backend-startup.ts
- apps/desktop/electron/renderer-bundle.ts
- apps/desktop/package.json
- apps/desktop/src/app/artifacts/artifact-utils.ts
- apps/desktop/src/app/chat/composer/index.tsx
- apps/desktop/src/app/chat/pane-mirror.ts
- apps/desktop/src/app/chat/preview-tile.test.ts
- apps/desktop/src/app/chat/preview-tile.tsx
- apps/desktop/src/app/chat/right-rail/preview-pane.tsx
- apps/desktop/src/app/contrib/hooks/use-desktop-integrations.ts
- apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts
- apps/desktop/src/app/right-sidebar/files/use-project-tree.test.ts
- apps/desktop/src/app/right-sidebar/files/use-project-tree.ts
- apps/desktop/src/app/right-sidebar/index.test.tsx
- apps/desktop/src/app/right-sidebar/index.tsx
- apps/desktop/src/app/session/hooks/use-hermes-config.test.ts
- apps/desktop/src/app/session/hooks/use-message-stream/clarify-hydration.test.tsx
- apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/input-requests.ts
- apps/desktop/src/components/assistant-ui/clarify-tool.test.tsx
- apps/desktop/src/components/assistant-ui/clarify-tool.tsx
- apps/desktop/src/components/assistant-ui/thread/streaming.test.tsx
- apps/desktop/src/global.d.ts
- apps/desktop/src/i18n/ar.ts
- apps/desktop/src/i18n/en.ts
- apps/desktop/src/i18n/ja.ts
- apps/desktop/src/i18n/types.ts
- apps/desktop/src/i18n/zh-hant.ts
- apps/desktop/src/i18n/zh.ts
- apps/desktop/src/lib/json-rpc-gateway-recovery.test.ts
- apps/desktop/src/plugins/hermes-bots/plugin.js
- apps/desktop/src/sdk/profile-routing.test.ts
- apps/desktop/src/store/clarify.ts
- apps/desktop/src/store/gateway-shared-remote.test.ts
- apps/desktop/src/store/gateway.ts
- apps/desktop/src/store/preview.test.ts
- apps/desktop/src/store/preview.ts
- apps/desktop/src/store/translucency.ts
- apps/desktop/src/styles.css
- apps/shared/src/json-rpc-gateway.ts
- cli-config.yaml.example
- cli.py
- cron/scheduler.py
- gateway/platforms/base.py
- gateway/run.py
- gateway/slash_commands.py
- hermes_cli/auth.py
- hermes_cli/config.py
- hermes_cli/config_defaults.py
- hermes_cli/doctor.py
- hermes_cli/main.py
- hermes_cli/mcp_config.py
- hermes_cli/models.py
- hermes_cli/plugins.py
- hermes_cli/profiles.py
- hermes_cli/setup.py
- hermes_cli/status.py
- hermes_cli/tools_config.py
- hermes_cli/web_models.py
- hermes_cli/web_server.py
- hermes_state.py
- pyproject.toml
- run_agent.py
- tests/agent/test_memory_provider.py
- tests/agent/test_stall_guards.py
- tests/conftest.py
- tests/gateway/test_platform_base.py
- tests/hermes_cli/test_gui_command.py
- tests/hermes_cli/test_mcp_catalog.py
- tests/hermes_cli/test_model_validation.py
- tests/hermes_cli/test_profiles.py
- tests/hermes_cli/test_relay_plugin_cutover.py
- tests/hermes_cli/test_tools_config.py
- tests/hermes_cli/test_web_server.py
- tests/run_agent/test_provider_fallback.py
- tests/test_hermes_constants.py
- tests/test_tui_gateway_server.py
- tests/tools/test_browser_npx_warmup.py
- tests/tools/test_computer_use.py
- tests/tools/test_docker_environment.py
- tools/approval.py
- tools/browser_tool.py
- tools/code_execution_tool.py
- tools/computer_use/cua_backend.py
- tools/cronjob_tools.py
- tools/environments/local.py
- tools/file_tools.py
- tools/lazy_deps.py
- tools/process_registry.py
- tools/send_message_tool.py
- tools/terminal_tool.py
- tools/web_tools.py
- toolsets.py
- tui_gateway/server.py
- tui_gateway/ws.py
- ui-tui/src/__tests__/gatewayClient.test.ts
- ui-tui/src/gatewayClient.ts
- uv.lock
- website/docs/getting-started/quickstart.md
- website/sidebars.ts

## Review boundary

UPSTREAM_ADOPTION.yaml is the commit-level authority. Decisions derive from
each commit subject, touched paths, and intersections with the downstream
delta. Semantic conflict resolution is excluded from this generator and must
preserve the policy files under .codex.
