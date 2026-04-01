# 2026-03-31 LINE migration log

- Worktree: `main`
- MCP datetime (UTC): `2026-03-31T15:26:33+00:00`

## Changes

- Added native LINE platform enum and env wiring:
  - `gateway/config.py`
  - New `Platform.LINE`
  - Env mapping: `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET`, `LINE_WEBHOOK_HOST`, `LINE_WEBHOOK_PORT`
- Added native LINE adapter:
  - `gateway/platforms/line.py`
  - Webhook endpoint: `POST /line/webhook`
  - Health endpoint: `GET /line/health`
  - Signature verification: `x-line-signature` (HMAC-SHA256 + base64)
  - Outbound send: LINE reply/push API (`/v2/bot/message/reply`, `/v2/bot/message/push`)
- Wired adapter into gateway runtime:
  - `gateway/run.py` adapter factory branch for `Platform.LINE`
  - Added allowlist env support:
    - `LINE_ALLOWED_USERS`
    - `LINE_ALLOW_ALL_USERS`
- Added env documentation:
  - `.env.example` LINE section

## Verification

- `py -3 -m hermes_cli.main gateway --help` succeeded.
- Env-to-config smoke test succeeded:
  - `Platform.LINE` resolved as enabled when LINE env vars are set.
  - Default webhook port resolved as `8650`.
