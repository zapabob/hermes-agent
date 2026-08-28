# Upstream snapshot integration, 2026-08-28

This report freezes the integration input. Commits newer than the recorded
upstream SHA are outside this campaign and must not be substituted.

## Snapshot

| Field | Value |
| --- | --- |
| Captured at | 2026-08-28T02:33:55+09:00 |
| Upstream head | 5fc308a70719a83cccdbba4c0e39c23f5a8239d5 |
| Downstream start | 4198d292cc1628383522ec201d4d55002da72f4f |
| Merge base | 1fe0f2f3ac9748ce799272eb93bee2937b5ab802 |
| Delta commits | 361 |
| Upstream-touched files | 493 |
| Fork intersections | 96 |

## Decision counts

| Decision | Commits |
| --- | ---: |
| ADOPT | 114 |
| COMPOSE | 202 |
| DEFER | 22 |
| IGNORE | 23 |
| KEEP_DOWNSTREAM | 0 |
| REPLACE_DOWNSTREAM | 0 |

## Category counts

| Category | Commits |
| --- | ---: |
| BUGFIX_RELEVANT | 216 |
| CREDENTIAL_BOUNDARY | 12 |
| DATA_INTEGRITY | 23 |
| DESKTOP_API_CHANGE | 133 |
| DOCS_ONLY | 24 |
| FEATURE_NEW_RELEVANT | 30 |
| FEATURE_OVERLAP | 202 |
| GATEWAY_API_CHANGE | 23 |
| MODEL_PROVIDER_CHANGE | 16 |
| PLATFORM_IRRELEVANT | 0 |
| PLUGIN_API_CHANGE | 46 |
| PUBLIC_API_CHANGE | 38 |
| SECURITY_CRITICAL | 23 |
| TEST_INFRA | 60 |
| WINDOWS_RELEVANT | 36 |

## Direct fork intersections

- agent/agent_init.py
- agent/auxiliary_client.py
- agent/context_compressor.py
- agent/conversation_loop.py
- agent/file_safety.py
- agent/model_metadata.py
- agent/prompt_builder.py
- agent/system_prompt.py
- agent/tool_executor.py
- apps/desktop/electron/app-icon.test.ts
- apps/desktop/electron/app-icon.ts
- apps/desktop/electron/hardening.test.ts
- apps/desktop/electron/main.ts
- apps/desktop/electron/preload.ts
- apps/desktop/src/app/chat/index.tsx
- apps/desktop/src/app/chat/sidebar/index.tsx
- apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts
- apps/desktop/src/app/session/hooks/use-model-controls.test.tsx
- apps/desktop/src/app/session/hooks/use-model-controls.ts
- apps/desktop/src/app/settings/gateway-settings.test.tsx
- apps/desktop/src/components/assistant-ui/clarify-tool.test.tsx
- apps/desktop/src/components/assistant-ui/clarify-tool.tsx
- apps/desktop/src/components/assistant-ui/markdown-text.artifacts.test.tsx
- apps/desktop/src/components/assistant-ui/thread/streaming.test.tsx
- apps/desktop/src/global.d.ts
- apps/desktop/src/i18n/ar.ts
- apps/desktop/src/i18n/en.ts
- apps/desktop/src/i18n/ja.ts
- apps/desktop/src/i18n/types.ts
- apps/desktop/src/i18n/zh-hant.ts
- apps/desktop/src/i18n/zh.ts
- apps/desktop/src/plugins/hermes-bots/plugin.js
- apps/desktop/src/sdk/profile-routing.test.ts
- apps/desktop/src/store/gateway.ts
- apps/desktop/src/store/updates.test.ts
- apps/desktop/src/styles.css
- cli-config.yaml.example
- cron/scheduler.py
- gateway/platforms/base.py
- gateway/platforms/bluebubbles.py
- gateway/platforms/whatsapp_cloud.py
- gateway/run.py
- gateway/slash_commands.py
- gateway/status.py
- hermes_cli/auth.py
- hermes_cli/backup.py
- hermes_cli/banner.py
- hermes_cli/cli_commands_mixin.py
- hermes_cli/config.py
- hermes_cli/config_defaults.py
- hermes_cli/doctor.py
- hermes_cli/gateway.py
- hermes_cli/main.py
- hermes_cli/models.py
- hermes_cli/plugins.py
- hermes_cli/setup.py
- hermes_cli/update_cmd.py
- hermes_cli/web_models.py
- hermes_cli/web_routers/mcp.py
- hermes_cli/web_server.py
- hermes_state.py
- package-lock.json
- package.json
- plugins/video_gen/fal/__init__.py
- pyproject.toml
- tests/agent/test_auxiliary_client.py
- tests/cron/test_cron_script.py
- tests/gateway/test_bluebubbles.py
- tests/gateway/test_slack.py
- tests/gateway/test_status.py
- tests/hermes_cli/test_backup.py
- tests/hermes_cli/test_config.py
- tests/hermes_cli/test_gateway.py
- tests/hermes_cli/test_managed_uv.py
- tests/hermes_cli/test_model_validation.py
- tests/hermes_cli/test_plugins.py
- tests/hermes_cli/test_update_stale_dashboard.py
- tests/hermes_cli/test_web_server.py
- tests/test_tui_gateway_server.py
- tests/tools/test_computer_use.py
- tests/tools/test_cronjob_tools.py
- tests/tools/test_mcp_tool.py
- tools/approval.py
- tools/browser_tool.py
- tools/code_execution_tool.py
- tools/computer_use/cua_backend.py
- tools/cronjob_tools.py
- tools/environments/base.py
- tools/environments/local.py
- tools/file_operations.py
- tools/file_tools.py
- tools/mcp_tool.py
- tools/process_registry.py
- tools/terminal_tool.py
- tui_gateway/server.py
- uv.lock

## Review boundary

UPSTREAM_ADOPTION.yaml is the commit-level authority. Decisions derive from
each commit subject, touched paths, and intersections with the downstream
delta. Semantic conflict resolution is excluded from this generator and must
preserve the policy files under .codex.
