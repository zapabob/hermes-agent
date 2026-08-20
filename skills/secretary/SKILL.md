---
name: secretary
description: "Coordinate A2A agents with deterministic greetings."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [secretary, a2a, coordination, agents, llmops]
    category: autonomous-ai-agents
    related_skills: [hermes-agent]
---

# secretary

**Secretary bot with seed42 memory base and random topic greetings for A2A agents**

## Description

The secretary bot operates on port 9902 as an A2A agent, using seed42 as a deterministic random seed for reproducible topic selection. It greets other A2A agents with random topics and proposes coordination adjustments. The bot maintains consistent behavior across sessions when using the same seed value, enabling reproducible random topic generation for bot coordination.

## Core Concepts

- **seed42 memory base**: Uses `random.seed(42)` for reproducible topic selection
- **A2A agent protocol**: Communicates with other A2A agents on configured ports
- **LLMOps daemon monitoring**: Monitors LLMOps daemon health and metrics
- **Round-robin NIM key routing**: Two NIM keys for NVIDIA Nemotron model routing

## Configuration

- **Port**: 9902 (configured in `.hermes/config.yaml` under `a2a_agents`)
- **NIM keys**: 2 NIM keys configured for round-robin routing
  - Both: `nvidia/nemotron-3.5-lightning-30b-a3b`, `provider: nvidia`
  - `api_key: ''` (redacted, belongs in `~/.hermes/.env` only)
- **Agent endpoints**: 
  - main-agent: http://127.0.0.1:9900
  - secretary: http://127.0.0.1:9902
  - sedori-buyer: http://127.0.0.1:9911
  - Additional agents at ports 9912-9916

## GREETING_TOPICS

The bot uses these 5 predefined topics for greetings and coordination proposals:

1. `daily-status-check` - Synchronize daily status updates and share blockers/progress
2. `resource-alignment` - Align resource allocations for the upcoming period
3. `timing-sync` - Verify timing synchronization and scheduled events
4. `workflow-optimization` - Explore workflow optimization and task streamlining
5. `status-update` - Provide brief status update for secretary's memory log

## Usage

### Commands

- `greet` - Send greetings to configured A2A agents with random topics
- `coordinate` - Propose coordination adjustments based on greeting topics
- `status` - Report current bot status and memory state

### Reproducibility

Using seed42 ensures the same topic ordering across sessions:
```
random.seed(42)  # Initialize deterministic RNG
topics = ["daily-status-check", "resource-alignment", "timing-sync", "workflow-optimization", "status-update"]
random.shuffle(topics)  # Same order every time with same seed
```

## Secrets

All secrets belong in `~/.hermes/.env` only (never commit):

```
GOOGLE_* / X_* / IRODORI_* credentials as needed
NIM api keys
```

## Related Skills

- `skills/autonomous-ai-agents/hermes-agent/SKILL.md` - Reference for A2A agent structure
- `plugin_index.json` - Contains hermes-telegram-business plugin described as "Observe-with-approval Telegram Business Mode (secretary bot) plugin"

## Version

0.1.0

## Author

Hermes Agent

## License

MIT

## Platforms

- Windows (primary)
- Cross-platform A2A communication
