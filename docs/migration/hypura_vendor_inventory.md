# Hypura / VRChat / Ollama Inventory

This inventory records the dependency and conflict map for native Hypura integration.

## Source Components

- `extensions/hypura-harness`
  - TypeScript plugin wrapper exposing HTTP tools against FastAPI daemon.
  - Python daemon entrypoint: `scripts/harness_daemon.py` (default `127.0.0.1:18794`).
  - Python dependencies declared in `scripts/pyproject.toml` include `fastapi`, `uvicorn`, `python-osc`, `httpx`, `redis`, plus optional LoRA stack (`torch`, `transformers`, `peft`, `trl`).
- `extensions/hypura-provider`
  - Registers provider id `hypura`, Ollama-compatible API at default `127.0.0.1:8080`.
- `extensions/vrchat-relay`
  - OSC and VRChat Web API integration with command/tool surface.
  - Uses OSC ports (`9000` outgoing, `9001` incoming by default).
- `extensions/ollama`
  - Native Ollama provider registration and model discovery flow.

## Hermes Existing Surfaces

- `hermes_cli/main.py`
  - Existing command tree is Python-first; no TypeScript plugin runtime parity with OpenClaw extensions.
- `gateway/run.py`
  - Messaging gateway is already present and should remain source-of-truth for messaging entrypoints.
- Existing migration features in `hermes_cli/claw.py` and docs under `docs/migration`.

## Conflict Map

- **Runtime Model**
  - OpenClaw extensions are TypeScript plugin entrypoints.
  - Hermes runtime is Python-centric CLI/gateway.
  - Resolution: expose Hypura/VRChat/Ollama as Hermes native CLI command group and optional runtime hooks.
- **Provider Duplication**
  - Hermes already has Ollama concepts; Hypura provider is also Ollama-compatible.
  - Resolution: add explicit Hypura profile/ENV keys and keep model provider choice explicit.
- **Environment Variables**
  - Need to add Hypura/VRChat-specific keys into Hermes `.env.example` while retaining prior alias handling.
- **Vendor Payload Size**
  - Full vendor mirror is large and may include build artifacts.
  - Resolution: mirror under namespaced path `vendor/openclaw-mirror/` to avoid collisions.

## Integration Decisions

- Integrate natively (no OpenClaw compatibility bridge).
- Mirror `vendor/` fully into Hermes as requested.
- Add Hermes-native command surface for:
  - Hypura daemon lifecycle and API calls
  - VRChat OSC actions via Hypura API
  - Ollama launch/health checks
