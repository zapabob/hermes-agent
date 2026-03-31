# Clawdbot -> Hermes Cutover Checklist

## Pre-cutover

- Run `hermes claw assess --source <clawdbot-repo> --output docs/migration`.
- Review `docs/migration/clawdbot_migration_assessment.md`.
- Confirm all `manual-port-required` extensions have an owner and migration path.
- Prepare a clean Hermes target (`~/.hermes` backup if already in use).

## Migration execution

1. Dry-run first:
   - `hermes claw migrate --source <openclaw-home> --dry-run --preset full`
2. Execute:
   - `hermes claw migrate --source <openclaw-home> --preset full --yes`
3. Archive legacy directory:
   - `hermes claw cleanup --source <openclaw-home> --yes`

## Validation

- Gateway startup succeeds.
- Required channels authenticate (`telegram`, `slack`, `discord` as applicable).
- Provider keys resolve correctly after env alias mapping.
- A basic tool call and memory read/write succeeds.
- Custom-ported modules (`vrchat-relay`, `hypura-*`, etc.) pass smoke tests.

## Rollback

- Keep the original OpenClaw directory as read-only backup until stable.
- If cutover fails:
  - Stop Hermes gateway/processes.
  - Restore previous `~/.hermes` backup.
  - Re-point runtime to archived OpenClaw directory.
  - Re-run dry-run with narrowed options to isolate failing segment.

## Recorded verification in this implementation

- Dry-run migration from `clawdbot-main` profile completed with zero errors.
- New `hermes claw assess` command tested and report generation validated.
- Env alias compatibility tests pass for OpenClaw gateway/API key aliases.
