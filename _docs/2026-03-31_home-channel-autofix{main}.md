# 2026-03-31 Home channel autofix log

- Worktree: `main`
- MCP datetime (UTC): `2026-03-31T15:34:26+00:00`

## Requested scope

- Discord / LINE / Telegram / VRChatOSC home-channel IDs
- No `gateway setup` dependency
- Auto-run-ready gateway state

## Actions performed

- Confirmed Telegram home channel ID and kept it fixed:
  - `TELEGRAM_HOME_CHANNEL=7201110294`
  - `platforms.telegram.home_channel.chat_id=7201110294`
- Attempted to extract Discord/LINE home channel concrete IDs from OpenClaw backups.
  - Result: no concrete Discord/LINE home chat/channel IDs persisted in source snapshots.
  - Kept placeholders in `.env` / `config.yaml` (empty IDs) to avoid incorrect routing.
- Added VRChat OSC default home routing envs:
  - `VRCHAT_OSC_ENABLED=true`
  - `VRCHAT_OSC_PORT=9000`
  - `VRCHAT_OSC_HOME_PLATFORM=telegram`
  - `VRCHAT_OSC_HOME_CHANNEL=7201110294`
- Added the same VRChat OSC env docs to `.env.example`.

## Gateway auto-run status

- `hermes gateway install` on this platform reports "Service installation not supported on this platform."
- Gateway currently runs manually and is active (`hermes gateway status` returns running PID).
