# Upstream snapshot integration, 2026-09-01

This report freezes the integration input. Commits newer than the recorded
upstream SHA are outside this campaign and must not be substituted.

## Snapshot

| Field | Value |
| --- | --- |
| Captured at | 2026-09-01T20:18:29+09:00 |
| Upstream head | 5a8e8a6b87487c0e0785cd9eb561cc6a96c64f5e |
| Downstream start | 2c9e426a59c02a6bbe7f9beab9fbfdf081e24bd7 |
| Merge base | 1fe0f2f3ac9748ce799272eb93bee2937b5ab802 |
| Comparison base | 5fc308a70719a83cccdbba4c0e39c23f5a8239d5 |
| Delta commits | 1049 |
| Upstream-touched files | 2093 |
| Downstream-touched files | 3001 |
| Fork intersections | 414 |

## Decision counts

| Decision | Commits |
| --- | ---: |
| ADOPT | 325 |
| ALREADY_PRESENT | 0 |
| COMPOSE | 723 |
| DEFER_PLATFORM | 1 |
| DOWNSTREAM_STRONGER | 0 |
| REJECT_GENERATED_ARTIFACT | 0 |

## Category counts

| Category | Commits |
| --- | ---: |
| BUGFIX_RELEVANT | 650 |
| CREDENTIAL_BOUNDARY | 57 |
| DATA_INTEGRITY | 87 |
| DESKTOP_API_CHANGE | 186 |
| DOCS_ONLY | 67 |
| FEATURE_NEW_RELEVANT | 92 |
| FEATURE_OVERLAP | 724 |
| GATEWAY_API_CHANGE | 109 |
| MODEL_PROVIDER_CHANGE | 87 |
| PLATFORM_IRRELEVANT | 1 |
| PLUGIN_API_CHANGE | 154 |
| PUBLIC_API_CHANGE | 73 |
| SECURITY_CRITICAL | 104 |
| TEST_INFRA | 179 |
| WINDOWS_RELEVANT | 28 |

## Direct fork intersections

- .env.example
- .github/workflows/ci.yaml
- .github/workflows/docker.yml
- .gitignore
- agent/agent_init.py
- agent/agent_runtime_helpers.py
- agent/anthropic_adapter.py
- agent/auxiliary_client.py
- agent/background_review.py
- agent/chat_completion_helpers.py
- agent/context_compressor.py
- agent/conversation_compression.py
- agent/conversation_loop.py
- agent/credential_pool.py
- agent/deadline.py
- agent/error_classifier.py
- agent/file_safety.py
- agent/image_routing.py
- agent/memory_manager.py
- agent/model_metadata.py
- agent/prompt_builder.py
- agent/reasoning_effort.py
- agent/system_prompt.py
- agent/tool_executor.py
- agent/transports/chat_completions.py
- agent/transports/codex.py
- agent/turn_context.py
- agent/web_search_registry.py
- apps/desktop/e2e/fixtures.ts
- apps/desktop/electron/backend-claim.test.ts
- apps/desktop/electron/connection-config.ts
- apps/desktop/electron/connection-registry.test.ts
- apps/desktop/electron/connection-registry.ts
- apps/desktop/electron/main.ts
- apps/desktop/electron/preload.ts
- apps/desktop/electron/ssh-connection.test.ts
- apps/desktop/package.json
- apps/desktop/src/api/profiles.ts
- apps/desktop/src/app/chat/composer/index.tsx
- apps/desktop/src/app/chat/composer/status-stack/index.tsx
- apps/desktop/src/app/chat/index.tsx
- apps/desktop/src/app/chat/pane-mirror.test.ts
- apps/desktop/src/app/chat/pane-mirror.ts
- apps/desktop/src/app/chat/preview-tile.test.ts
- apps/desktop/src/app/chat/right-rail/preview-pane.tsx
- apps/desktop/src/app/chat/route-tile.tsx
- apps/desktop/src/app/chat/sidebar/connection-glyph.tsx
- apps/desktop/src/app/chat/sidebar/index.tsx
- apps/desktop/src/app/chat/sidebar/profile-switcher.tsx
- apps/desktop/src/app/chat/sidebar/projects/workspace-groups.test.ts
- apps/desktop/src/app/chat/sidebar/projects/workspace-groups.ts
- apps/desktop/src/app/chat/sidebar/sessions-section.tsx
- apps/desktop/src/app/chat/sidebar/virtual-session-list.tsx
- apps/desktop/src/app/command-center/index.tsx
- apps/desktop/src/app/command-palette/index.tsx
- apps/desktop/src/app/contrib/hooks/use-session-tile-delegate.ts
- apps/desktop/src/app/contrib/session-rpc-dispatcher.test.ts
- apps/desktop/src/app/contrib/session-rpc-dispatcher.ts
- apps/desktop/src/app/contrib/surfaces.tsx
- apps/desktop/src/app/contrib/wiring.tsx
- apps/desktop/src/app/profiles/delete-profile-dialog.tsx
- apps/desktop/src/app/session/hooks/profile-rail-fresh-chat-owner.test.tsx
- apps/desktop/src/app/session/hooks/use-message-stream/clarify-hydration.test.tsx
- apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/desktop-bridge.ts
- apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/index.ts
- apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/input-requests.ts
- apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/lifecycle.ts
- apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/session-info.ts
- apps/desktop/src/app/session/hooks/use-message-stream/index.ts
- apps/desktop/src/app/session/hooks/use-message-stream/utils.ts
- apps/desktop/src/app/session/hooks/use-model-controls.test.tsx
- apps/desktop/src/app/session/hooks/use-model-controls.ts
- apps/desktop/src/app/session/hooks/use-prompt-actions/slash.ts
- apps/desktop/src/app/session/hooks/use-prompt-actions/submit.ts
- apps/desktop/src/app/session/hooks/use-session-actions.test.tsx
- apps/desktop/src/app/session/hooks/use-session-actions/index.ts
- apps/desktop/src/app/session/hooks/use-session-state-cache.ts
- apps/desktop/src/app/settings/constants.ts
- apps/desktop/src/app/settings/model-settings.test.tsx
- apps/desktop/src/app/settings/model-settings.tsx
- apps/desktop/src/app/shell/model-menu-panel.test.tsx
- apps/desktop/src/app/shell/model-menu-panel.tsx
- apps/desktop/src/app/shell/titlebar-controls.tsx
- apps/desktop/src/app/skills/index.test.tsx
- apps/desktop/src/app/types.ts
- apps/desktop/src/components/assistant-ui/clarify-tool.test.tsx
- apps/desktop/src/components/assistant-ui/clarify-tool.tsx
- apps/desktop/src/components/assistant-ui/markdown-text.tsx
- apps/desktop/src/components/chat/intro.tsx
- apps/desktop/src/components/pane-shell/tree/renderer/tree-group.tsx
- apps/desktop/src/global.d.ts
- apps/desktop/src/hermes-capability-scope.test.ts
- apps/desktop/src/i18n/ar.ts
- apps/desktop/src/i18n/en.ts
- apps/desktop/src/i18n/ja.ts
- apps/desktop/src/i18n/types.ts
- apps/desktop/src/i18n/zh-hant.ts
- apps/desktop/src/i18n/zh.ts
- apps/desktop/src/lib/desktop-slash-commands.test.ts
- apps/desktop/src/lib/desktop-slash-commands.ts
- apps/desktop/src/lib/external-link.tsx
- apps/desktop/src/lib/model-options.test.ts
- apps/desktop/src/lib/model-options.ts
- apps/desktop/src/plugins/hermes-bots/plugin.js
- apps/desktop/src/plugins/hermes-bots/tests/94478-mention-settle.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/active-now-strip.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/activity-toasts.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/bot-attention-badge.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/bots-home.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/canonical-chat-adopt-on-conflict.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/canonical-chat-creation.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/canonical-chat-registry.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/embed-skills-view.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/group-activity.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/group-chat-empty-sentinel.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/group-chat.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/group-stop-thread.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/group-to-local-bot-handoff.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/group-turn-lease.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/legacy-member-normalize.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/mention-renamed-bots.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/model-picker-settle.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/model-switch-confirm.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/multi-source-roster.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/remote-routing-races.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/roster-groups.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/routine-prompt.test.mjs
- apps/desktop/src/plugins/hermes-bots/tests/unaddressed-mentions.test.mjs
- apps/desktop/src/sdk/index.ts
- apps/desktop/src/sdk/profile-routing.test.ts
- apps/desktop/src/store/composer-status.ts
- apps/desktop/src/store/gateway.ts
- apps/desktop/src/store/mcp-health.ts
- apps/desktop/src/store/profile-agent-activation.test.ts
- apps/desktop/src/store/profile-select-source.test.ts
- apps/desktop/src/store/profile.ts
- apps/desktop/src/store/prompts.ts
- apps/desktop/src/store/session-states.test.ts
- apps/desktop/src/store/session-states.ts
- apps/desktop/src/store/session.test.ts
- apps/desktop/src/store/session.ts
- apps/desktop/src/styles.css
- apps/desktop/src/themes/context.tsx
- apps/desktop/src/types/hermes.ts
- apps/desktop/vite.config.ts
- apps/desktop/vitest.config.ts
- apps/shared/src/json-rpc-gateway.ts
- cli-config.yaml.example
- cli.py
- contributors/emails/[redacted-8f561b784998]
- contributors/emails/[redacted-f5dfe7aee708]
- cron/jobs.py
- cron/scheduler.py
- cron/scheduler_provider.py
- evals/browser_use/single_run.py
- gateway/authz_mixin.py
- gateway/config.py
- gateway/platforms/api_server.py
- gateway/platforms/base.py
- gateway/platforms/bluebubbles.py
- gateway/platforms/qqbot/adapter.py
- gateway/platforms/webhook.py
- gateway/platforms/weixin.py
- gateway/platforms/whatsapp_cloud.py
- gateway/platforms/yuanbao.py
- gateway/relay/adapter.py
- gateway/run.py
- gateway/session.py
- gateway/slash_commands.py
- gateway/status.py
- hermes_cli/__init__.py
- hermes_cli/auth.py
- hermes_cli/backup.py
- hermes_cli/browser_connect.py
- hermes_cli/cli_agent_setup_mixin.py
- hermes_cli/cli_commands_mixin.py
- hermes_cli/commands.py
- hermes_cli/config.py
- hermes_cli/config_defaults.py
- hermes_cli/credential_lifecycle.py
- hermes_cli/cron.py
- hermes_cli/dashboard_procs.py
- hermes_cli/debug.py
- hermes_cli/doctor.py
- hermes_cli/dump.py
- hermes_cli/gateway.py
- hermes_cli/inventory.py
- hermes_cli/kanban_db.py
- hermes_cli/macos_tcc_anchor.py
- hermes_cli/main.py
- hermes_cli/managed_uv.py
- hermes_cli/model_normalize.py
- hermes_cli/model_switch.py
- hermes_cli/models.py
- hermes_cli/nous_subscription.py
- hermes_cli/plugins.py
- hermes_cli/profiles.py
- hermes_cli/providers.py
- hermes_cli/runtime_provider.py
- hermes_cli/setup.py
- hermes_cli/status.py
- hermes_cli/tools_config.py
- hermes_cli/update_cmd.py
- hermes_cli/web_routers/profiles.py
- hermes_cli/web_routers/sessions.py
- hermes_cli/web_server.py
- hermes_cli/worktree_gc.py
- hermes_logging.py
- hermes_state.py
- locales/af.yaml
- locales/ar.yaml
- locales/de.yaml
- locales/en.yaml
- locales/es.yaml
- locales/fr.yaml
- locales/ga.yaml
- locales/hu.yaml
- locales/it.yaml
- locales/ja.yaml
- locales/ko.yaml
- locales/pt.yaml
- locales/ru.yaml
- locales/tr.yaml
- locales/uk.yaml
- locales/zh-hant.yaml
- locales/zh.yaml
- model_tools.py
- optional-skills/software-development/code-wiki/SKILL.md
- package-lock.json
- package.json
- plugins/model-providers/alibaba-coding-plan/__init__.py
- plugins/model-providers/alibaba/__init__.py
- plugins/model-providers/nebius-token-factory/__init__.py
- plugins/model-providers/nebius-token-factory/plugin.yaml
- plugins/model-providers/router/__init__.py
- plugins/model-providers/router/plugin.yaml
- plugins/platforms/discord/adapter.py
- plugins/platforms/line/adapter.py
- plugins/platforms/photon/README.md
- plugins/platforms/photon/adapter.py
- plugins/platforms/photon/sidecar/index.mjs
- plugins/platforms/photon/sidecar/patch-spectrum-mixed-attachments.mjs
- plugins/platforms/slack/adapter.py
- plugins/platforms/wecom/adapter.py
- plugins/platforms/whatsapp/adapter.py
- plugins/video_gen/fal/__init__.py
- plugins/web/brave_free/provider.py
- plugins/web/xai/provider.py
- providers/README.md
- providers/base.py
- pyproject.toml
- run_agent.py
- scripts/ci/classify_changes.py
- scripts/desktop-update/posix.sh
- scripts/desktop-update/windows.ps1
- scripts/install.ps1
- scripts/install.sh
- scripts/release.py
- setup-hermes.sh
- skills/autonomous-ai-agents/computer-use/SKILL.md
- skills/github/DESCRIPTION.md
- skills/mlops/DESCRIPTION.md
- skills/research/grounded-citations/SKILL.md
- tests/agent/test_auxiliary_client.py
- tests/agent/test_codex_app_server_persist.py
- tests/agent/test_compression_concurrent_fork.py
- tests/agent/test_compression_review_76354.py
- tests/agent/test_context_compressor.py
- tests/agent/test_deadline.py
- tests/agent/test_model_metadata.py
- tests/agent/test_opencode_free_provider.py
- tests/agent/test_skill_commands.py
- tests/agent/transports/test_router_codex_efforts.py
- tests/ci/test_classify_changes.py
- tests/cli/test_cli_approval_ui.py
- tests/cli/test_cli_background_status_indicator.py
- tests/cli/test_cli_browser_connect.py
- tests/conftest.py
- tests/cron/test_87033_cronjob_gateway_liveness.py
- tests/cron/test_claim_job_for_fire.py
- tests/cron/test_cron_inactivity_timeout.py
- tests/cron/test_cron_workdir.py
- tests/cron/test_scheduler.py
- tests/cron/test_script_claim_heartbeat.py
- tests/gateway/relay/test_relay_slack_unfurl.py
- tests/gateway/test_agent_cache.py
- tests/gateway/test_api_server.py
- tests/gateway/test_config.py
- tests/gateway/test_config_env_bridge_authority.py
- tests/gateway/test_platform_base.py
- tests/gateway/test_resume_command.py
- tests/gateway/test_runner_startup_failures.py
- tests/gateway/test_status.py
- tests/gateway/test_turn_lease.py
- tests/gateway/test_update_command.py
- tests/gateway/test_wecom.py
- tests/gateway/test_whatsapp_connect.py
- tests/hermes_cli/test_active_sessions.py
- tests/hermes_cli/test_api_key_providers.py
- tests/hermes_cli/test_apply_profile_override.py
- tests/hermes_cli/test_browser_connect_default_chromium.py
- tests/hermes_cli/test_cmd_update.py
- tests/hermes_cli/test_commands.py
- tests/hermes_cli/test_config.py
- tests/hermes_cli/test_credential_lifecycle.py
- tests/hermes_cli/test_dashboard_admin_endpoints.py
- tests/hermes_cli/test_gateway.py
- tests/hermes_cli/test_gateway_service.py
- tests/hermes_cli/test_gui_command.py
- tests/hermes_cli/test_inventory.py
- tests/hermes_cli/test_macos_tcc_anchor.py
- tests/hermes_cli/test_managed_uv.py
- tests/hermes_cli/test_model_validation.py
- tests/hermes_cli/test_nebius_token_factory_provider.py
- tests/hermes_cli/test_opencode_free_live_catalog.py
- tests/hermes_cli/test_opencode_zen_free_keyless.py
- tests/hermes_cli/test_plugins.py
- tests/hermes_cli/test_profiles.py
- tests/hermes_cli/test_router_provider.py
- tests/hermes_cli/test_set_config_value.py
- tests/hermes_cli/test_status.py
- tests/hermes_cli/test_tcc_anchor_revert.py
- tests/hermes_cli/test_tencent_tokenhub_provider.py
- tests/hermes_cli/test_tools_config.py
- tests/hermes_cli/test_update_concurrent_quarantine.py
- tests/hermes_cli/test_update_stale_dashboard.py
- tests/hermes_cli/test_web_server.py
- tests/plugins/web/test_web_search_provider_plugins.py
- tests/providers/test_plugin_discovery.py
- tests/providers/test_provider_profiles.py
- tests/run_agent/test_413_compression.py
- tests/run_agent/test_codex_app_server_compaction.py
- tests/run_agent/test_provider_fallback.py
- tests/skills/test_openclaw_migration.py
- tests/state/test_fts_runtime_rebuild.py
- tests/test_tui_gateway_server.py
- tests/tools/test_approval.py
- tests/tools/test_browser_homebrew_paths.py
- tests/tools/test_browser_real_profile.py
- tests/tools/test_code_execution.py
- tests/tools/test_computer_use_cua_0_10_permissions.py
- tests/tools/test_cronjob_tools.py
- tests/tools/test_docker_environment.py
- tests/tools/test_file_tools.py
- tests/tools/test_hermes_subprocess_env.py
- tests/tools/test_local_env_blocklist.py
- tests/tools/test_process_registry.py
- tests/tools/test_skills_guard.py
- tests/tools/test_skills_hub.py
- tests/tools/test_subprocess_stdin_guard.py
- tests/tools/test_web_providers.py
- tests/tools/test_web_providers_ddgs.py
- tests/tools/test_web_providers_xai.py
- tests/tools/test_web_tools_config.py
- tests/tools/test_web_tools_tavily.py
- tests/tools/test_windows_native_support.py
- tests/tui_gateway/test_compression_config_hot_reload.py
- tests/tui_gateway/test_custom_provider_session_persistence.py
- tools/approval.py
- tools/browser_cdp_tool.py
- tools/browser_tool.py
- tools/browser_use_cli.py
- tools/code_execution_tool.py
- tools/computer_use/cua_backend.py
- tools/cronjob_tools.py
- tools/environments/base.py
- tools/environments/local.py
- tools/file_tools.py
- tools/lazy_deps.py
- tools/mcp_oauth_manager.py
- tools/mcp_tool.py
- tools/process_registry.py
- tools/read_extract.py
- tools/send_message_tool.py
- tools/skill_manager_tool.py
- tools/skills_guard.py
- tools/skills_hub.py
- tools/terminal_tool.py
- tools/url_safety.py
- tools/vision_tools.py
- tools/web_tools.py
- toolsets.py
- tui_gateway/methods_bot_relay.py
- tui_gateway/methods_complete.py
- tui_gateway/methods_profiles.py
- tui_gateway/methods_prompt.py
- tui_gateway/methods_tools.py
- tui_gateway/server.py
- tui_gateway/ws.py
- ui-tui/src/__tests__/appChromeBlockedTimers.test.tsx
- ui-tui/src/app/useMainApp.ts
- ui-tui/src/gatewayTypes.ts
- utils.py
- uv.lock
- website/docs/developer-guide/adding-providers.md
- website/docs/developer-guide/context-compression-and-caching.md
- website/docs/getting-started/installation.md
- website/docs/getting-started/quickstart.md
- website/docs/integrations/providers.md
- website/docs/reference/cli-commands.md
- website/docs/reference/environment-variables.md
- website/docs/reference/slash-commands.md
- website/docs/user-guide/cli.md
- website/docs/user-guide/configuration.md
- website/docs/user-guide/desktop.md
- website/docs/user-guide/features/computer-use.md
- website/docs/user-guide/features/cron.md
- website/docs/user-guide/features/kanban.md
- website/docs/user-guide/messaging/slack.md
- website/docs/user-guide/profile-distributions.md
- website/docs/user-guide/skills/bundled/social-media/social-media-xurl.md
- website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/skills/bundled/research/research-research-paper-writing.md
- website/sidebars.ts
- website/static/api/model-catalog.json

## Review boundary

UPSTREAM_ADOPTION.yaml is the commit-level authority. Decisions derive from
each commit subject, touched paths, and intersections with the downstream
delta. Semantic conflict resolution is excluded from this generator and must
preserve the policy files under .codex.
