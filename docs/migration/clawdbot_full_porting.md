# Clawdbot Full Porting Runbook

This runbook captures the concrete implementation path for migrating a custom `clawdbot-main` fork into Hermes.

## 1) Inventory + Classification

Run:

```bash
hermes claw assess --source /path/to/clawdbot-main --output docs/migration
```

Generated artifacts:
- `docs/migration/clawdbot_migration_assessment.json`
- `docs/migration/clawdbot_migration_assessment.md`

Current assessment snapshot (from `clawdbot-main`):
- 91 extensions discovered
- 31 `native-or-direct-mapping`
- 10 `manual-port-required`
- 50 `needs-review`
- 44 source env keys, 6 direct overlaps with Hermes `.env.example`

## 2) Dry-Run Migration (OpenClaw-Compatible Layer)

Dry-run command used:

```powershell
$env:MIGRATION_JSON_OUTPUT='1'
$env:PYTHONIOENCODING='utf-8'
py -3 optional-skills/migration/openclaw-migration/scripts/openclaw_to_hermes.py `
  --source "C:\Users\downl\Desktop\clawdbot-main3\clawdbot-main\.openclaw-desktop" `
  --target "C:\Users\downl\Desktop\hermes-agent-main\hermes-agent-main\.tmp_hermes_migration_target" `
  --preset full
```

Observed result:
- migrated: 95
- archived: 4
- skipped: 25
- conflict: 0
- error: 0

## 3) Environment Variable Unification

Hermes now supports compatibility aliases at load time (`hermes_cli/env_loader.py`):
- `OPENCLAW_GATEWAY_TOKEN` -> `HERMES_GATEWAY_TOKEN`
- `XI_API_KEY` -> `ELEVENLABS_API_KEY`
- `OPENCLAW_LIVE_OPENAI_KEY` -> `OPENAI_API_KEY`
- `OPENCLAW_LIVE_ANTHROPIC_KEY` -> `ANTHROPIC_API_KEY`
- `OPENCLAW_LIVE_GEMINI_KEY` -> `GEMINI_API_KEY`

These aliases only apply when the Hermes-native key is not already set.

## 4) Custom Extension Porting Backlog

The following source extensions are classified as `manual-port-required` and should be moved as Hermes skills, gateway integrations, or dedicated CLI flows:

- `auto-agent`
- `hypura-harness`
- `hypura-provider`
- `live2d-companion`
- `local-voice`
- `python-exec`
- `universal-skills`
- `voice-call`
- `vrchat-relay`
- `x-poster`

Recommended order:
1. `vrchat-relay` + `hypura-harness` (highest behavior delta)
2. `local-voice` + `voice-call` (media/runtime coupling)
3. `python-exec` + `auto-agent` (execution policy impact)
4. remaining UX/aggregation extensions

## 5) Validation Checklist

- Run migration dry-run and confirm zero errors.
- Confirm gateway auth and channel allowlists after alias loading.
- Smoke test Telegram/Slack/Discord paths.
- Smoke test custom-ported modules one by one (feature flags preferred).
- Keep original OpenClaw directory archived (read-only fallback) until cutover stability is confirmed.
