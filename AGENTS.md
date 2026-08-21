# Hermes Agent - Development Guide

Instructions for AI coding assistants and developers working on the `hermes-agent` codebase.

**Never give up on the right solution.**

---

## 1. What Hermes Is & Core Philosophy

Hermes is a personal AI agent that runs the same agent core across a CLI, a messaging gateway (Telegram, Discord, Slack, LINE, WeCom, Weixin, Yuanbao, and ~20 other platforms), a TUI, and an Electron desktop app. It learns across sessions (memory + skills), delegates to subagents, runs scheduled jobs, and drives a real terminal and browser. It is extended primarily through **plugins and skills**, not by growing the core.

Two sacred properties shape almost every design decision and are the lens for reviewing any change:

- **Per-conversation prompt caching is sacred.** A long-lived conversation reuses a cached prefix every turn. Anything that mutates past context, swaps toolsets, or rebuilds the system prompt mid-conversation invalidates that cache and multiplies the user's cost. We do not do it (the one exception is context compression).
- **The core is a narrow waist; capability lives at the edges.** Every model tool we add is sent on every API call, so the bar for a new *core* tool is high. Most new capability should arrive as a CLI command + skill, a service-gated tool (`check_fn`), or a plugin — not as core surface.

---

## 2. Contribution Rubric — What We Want / What We Don't

This is the project's intent layer. Use it for humans (targeting contributions) and automated review (safe closes on `implemented_on_main`, `cannot_reproduce`, `incoherent`). Taste-based "won't-implement" closes stay with human maintainers.

Hermes ships a lot — most merges are bug fixes to reported behavior, and the product surface (platforms, channels, providers, models, desktop/TUI) expands aggressively. Restraint is aimed squarely at the **core agent + model tool schema**. We are expansive at the edges and conservative at the waist.

### What We Want
- **Fix real bugs, well**: Reproduce against current `main`, pinpoint the exact manifesting line, and fix the whole bug class across sibling call paths.
- **Expand reach at the edges**: New platform adapters, channels, providers, models, and desktop/TUI features integrating with standard setup/config (`hermes tools`, `hermes setup`, auto-install) rather than bolting on raw env vars.
- **Refactor god-files into clean modules**: Extract multi-thousand-line clusters out of `cli.py`, `run_agent.py`, `gateway/run.py` into focused mixins or modules.
- **Extend, don't duplicate**: Check existing infrastructure before adding managers/hooks. When 3+ PRs integrate the same category, design a shared ABC + orchestrator.
- **Behavior contracts over snapshots**: Assert invariants between data, not frozen values (model lists, config version literals, enumeration counts).
- **E2E validation**: Exercise real resolution chains with real imports against a temporary `HERMES_HOME` (mocks hide integration bugs).
- **Cache-, alternation-, and invariant-safe**: Preserve prompt caching, strict message role alternation, and byte-stable system prompts.
- **Contributor credit preserved**: Rebase-merge external work to keep authorship in git history.

### What We Don't Want (Rejected Even If Well-Built)
- **Speculative infrastructure**: Hooks, callbacks, or extension points with no concrete consumer.
- **New `HERMES_*` env vars for non-secret config**: `.env` is strictly for secrets (API keys, tokens, passwords). All behavioral settings (timeouts, thresholds, feature flags, display prefs) go in `config.yaml`.
- **A new core tool when terminal + file or a skill suffices**: Fix the mount or write a skill instead.
- **Lazy-reading escape hatches on instructional tools**: No `offset`/`limit` pagination on skills/prompts (models read page 1 and skip the rest).
- **Mitigations that destroy feature utility**: Always read original commit intent (`git log -p -S`) before restricting behavior.
- **Outbound telemetry without opt-in gating**: No analytics or attribution tags without a user-facing config gate and setup toggle.
- **Core-modifying plugins or in-tree third-party SaaS integrations**: Observability backends, vendor SaaS connectors, and analytics dashboards must live in **standalone plugin repos** (`~/.hermes/plugins/`), not under `plugins/` in this tree.

### Verify the Premise Before Calling It a Bug
- **"Intentional design, not a gap"**: Limitations are often deliberate (e.g. isolated profiles vs. shared live inheritance). Check commit intent before assuming something is unfinished.
- **"The premise doesn't hold against how X actually works"**: Trace runtime execution before accepting a rationale (e.g. rate-limit breakers tripping on confirmed-empty buckets). Point to the exact line where the bug manifests.
- **"The absence was deliberate"**: Restoring seemingly missing files (e.g. `__init__.py`) can break import shadowing guards and delete plugin `register()`.

### The Footprint Ladder (New Capability Decision)
Each rung adds more permanent surface than the one above. Choose the highest (least-footprint) rung:
1. **Extend existing code** — Zero new surface.
2. **CLI command + skill** — Zero model-tool footprint. Default choice for subscriptions, cron tasks, service setup (`hermes webhook`, `hermes cron`, `hermes tools`).
3. **Service-gated tool (`check_fn`)** — Structured I/O appearing only when prerequisites are configured (Home Assistant, memory tools).
4. **Plugin** — Third-party or user-specific capability in `~/.hermes/plugins/` or a pip package.
5. **MCP server (in catalog)** — Structured model tool connecting via built-in MCP client; zero core schema footprint.
6. **New core tool** — Fundamental, universally useful, and unreachable via terminal/file/MCP (`terminal`, `read_file`, `web_search`, `browser_navigate`).

### Surface Capability Is a Property of the Session, Never Process Env
Tools requiring client presence (desktop panes, in-app browser, reactions, projects) must resolve availability from the **session's own source**, not from an environment variable (`HERMES_DESKTOP=1`) on the backend process.
- **The toolset is the surface gate**: Keep tools off `_HERMES_CORE_TOOLS` and put them in a named toolset (`desktop_ui`, `project`). The GUI gateway folds them in when `platform` indicates GUI.
- **`check_fn` answers reachability or opt-in, not surface**: "Is the bridge wired?" is fine; "Was I spawned by Electron?" is not (cached process-wide across sessions).

---

## 3. Development Environment & Project Structure

```bash
# Prefer .venv; fall back to venv if present
source .venv/bin/activate   # or: source venv/bin/activate
```
`scripts/run_tests.sh` probes `.venv`, `venv`, and `$HOME/.hermes/hermes-agent/venv`.

### Project Layout
```
hermes-agent/
├── run_agent.py          # AIAgent class — core conversation loop (~12k LOC)
├── model_tools.py        # Tool orchestration, discover_builtin_tools(), handle_function_call()
├── toolsets.py           # Toolset definitions, _HERMES_CORE_TOOLS list
├── cli.py                # HermesCLI class — interactive CLI orchestrator (~11k LOC)
├── hermes_state.py       # SessionDB — SQLite session store (FTS5 search)
├── hermes_constants.py   # get_hermes_home(), display_hermes_home() — profile-aware paths
├── hermes_logging.py     # setup_logging() — agent.log / errors.log / gateway.log (profile-aware)
├── batch_runner.py       # Parallel batch processing engine
├── agent/                # Agent internals (adapters, memory, caching, compression, prompt builder)
├── hermes_cli/           # CLI subcommands, setup wizard, plugins loader, skin engine
├── tools/                # Tool implementations — auto-discovered via tools/registry.py
│   └── environments/     # Terminal backends (local, docker, ssh, modal, daytona, singularity)
├── gateway/              # Messaging gateway — run.py + session.py + platforms/
│   ├── platforms/        # Adapters: telegram, discord, slack, line, wecom, weixin, feishu, etc.
│   └── builtin_hooks/    # Extension points for gateway lifecycle hooks
├── plugins/              # Plugin system (memory/, model-providers/, context_engine/, kanban/, etc.)
├── optional-skills/      # Heavier/niche skills shipped but NOT active by default
├── skills/               # Built-in skills bundled with the repo
├── ui-tui/               # Ink (React) terminal UI — `hermes --tui`
│   └── src/              # entry.tsx, app.tsx, gatewayClient.ts + components/hooks
├── tui_gateway/          # Python JSON-RPC backend for the TUI
├── acp_adapter/          # ACP server (VS Code / Zed / JetBrains integration)
├── cron/                 # Scheduler — jobs.py, scheduler.py (via croniter)
├── scripts/              # run_tests.sh, release tooling, windows/ automation
├── website/              # Docusaurus documentation site
└── tests/                # Pytest suite (~17k tests across ~900 files)
```

**User config:** `~/.hermes/config.yaml` (settings), `~/.hermes/.env` (API keys only).
**Logs:** `~/.hermes/logs/` — `agent.log` (INFO+), `errors.log` (WARNING+), `gateway.log`. Profile-aware via `get_hermes_home()`. Browse with `hermes logs [--follow] [--level ...] [--session ...]`.

---

## 4. TypeScript Style Guide

Applies to TypeScript across Hermes (desktop, TUI, website, shared TS packages):
- Prefer small nanostores over component state when shared, reused, or read by distant UI.
- Each feature owns its atoms: Chat state near chat, shell state near shell, shared state in `src/store`.
- Components rendering from an atom use `useStore`. Non-rendering actions read with `$atom.get()`.
- Do not prop-drill across 3 components when a leaf can subscribe to an atom.
- Keep route roots thin (compose routes and shell; never turn into controllers). No monolithic hooks.
- Colocate action modules over hidden god hooks.
- Pure side-effect callbacks use terse void form: `onState={st => void setGatewayState(st)}`.
- Async UI handlers make intent explicit: `onClick={() => void save()}`.
- Prefer `interface` for public props and shared object shapes. Extend React primitives: `React.ComponentProps<'button'>`, `React.ComponentProps<typeof Dialog>`, `Omit<...>`, `Pick<...>`.
- Table-driven mapping beats condition ladders when routing views.
- Architecture: `src/app` (routes/pages), `src/store` (shared atoms), `src/lib` (pure helpers).

---

## 5. Core Agent Architecture & Execution Loop

```
tools/registry.py  (no deps — imported by all tool files)
       ↑
tools/*.py  (each calls registry.register() at import time)
       ↑
model_tools.py  (imports tools/registry + triggers tool discovery)
       ↑
run_agent.py, cli.py, batch_runner.py, environments/
```

### AIAgent Class (`run_agent.py`)
```python
class AIAgent:
    def __init__(self,
        base_url: str = None,
        api_key: str = None,
        provider: str = None,
        api_mode: str = None,              # "chat_completions" | "codex_responses" | ...
        model: str = "",                   # empty → resolved from config/provider later
        max_iterations: int = 500,         # tool-calling iterations (shared with subagents)
        enabled_toolsets: list = None,
        disabled_toolsets: list = None,
        quiet_mode: bool = False,
        save_trajectories: bool = False,
        platform: str = None,              # "cli", "telegram", etc.
        session_id: str = None,
        skip_context_files: bool = False,
        skip_memory: bool = False,
        credential_pool=None,
        # ... callbacks, budgets, reasoning_config, service_tier, checkpoints
    ): ...

    def chat(self, message: str) -> str:
        """Simple interface — returns final response string."""

    def run_conversation(self, user_message: str, system_message: str = None,
                         conversation_history: list = None, task_id: str = None) -> dict:
        """Full interface — returns dict with final_response + messages."""
```

### Conversation Loop
Entirely synchronous within `run_conversation()`, enforcing interrupts, budget tracking, and a one-turn grace call:
```python
while (api_call_count < self.max_iterations and self.iteration_budget.remaining > 0) \
        or self._budget_grace_call:
    if self._interrupt_requested: break
    response = client.chat.completions.create(model=model, messages=messages, tools=tool_schemas)
    if response.tool_calls:
        for tool_call in response.tool_calls:
            result = handle_function_call(tool_call.name, tool_call.args, task_id)
            messages.append(tool_result_message(result))
        api_call_count += 1
    else:
        return response.content
```
Messages follow standard OpenAI dictionary format: `{"role": "system/user/assistant/tool", ...}`. Model reasoning thoughts are stored in `assistant_msg["reasoning"]`.

---

## 6. CLI, TUI & Desktop Architecture

### CLI (`cli.py`)
- Rich panels and banners; `prompt_toolkit` for input with autocomplete.
- `KawaiiSpinner` (`agent/display.py`) animated status faces; `┊` tool activity feed.
- `load_cli_config()` merges defaults with user YAML.
- Data-driven skin engine (`hermes_cli/skin_engine.py`) configured via `display.skin`.
- Skill slash commands (`agent/skill_commands.py`) scan `~/.hermes/skills/` and inject as **user messages** to preserve prompt cache.

### Slash Command Registry (`hermes_cli/commands.py`)
Defined centrally in `COMMAND_REGISTRY` as `CommandDef` objects:
```python
CommandDef(
    name="mycommand",
    description="Description of command",
    category="Session",            # Session, Configuration, Tools & Skills, Info, Exit
    aliases=("mc",),
    args_hint="[arg]",
    cli_only=False,
    gateway_only=False,
    gateway_config_gate=None,
)
```
- **CLI**: `process_command()` resolves aliases via `resolve_command()`.
- **Gateway**: `GATEWAY_KNOWN_COMMANDS` for hook emission and routing in `gateway/run.py`.
- **Adding an alias**: Add to `aliases` tuple on `CommandDef`. Help, menus, autocomplete, and dispatch update automatically.

### TUI Architecture (`ui-tui` + `tui_gateway`)
Activated via `hermes --tui` or `HERMES_TUI=1`. Node (Ink) manages screen layout and transcript rendering; Python (`tui_gateway`) supervises sessions, tools, and model calls over stdio JSON-RPC.

| Surface | Ink Component | Gateway JSON-RPC Method |
| :--- | :--- | :--- |
| **Chat Streaming** | `app.tsx` + `messageLine.tsx` | `prompt.submit` → `message.delta/complete` |
| **Tool Activity** | `thinking.tsx` | `tool.start/progress/complete` |
| **Approvals** | `prompts.tsx` | `approval.respond` ← `approval.request` |
| **Clarify/Secret** | `prompts.tsx`, `maskedPrompt.tsx` | `clarify/sudo/secret.respond` |
| **Session Picker**| `sessionPicker.tsx` | `session.list/resume` |
| **Slash Execution**| Local handler + worker | `slash.exec` → `_SlashWorker`, `command.dispatch` |

Embedded in web dashboard (`hermes dashboard` → `/chat`) via WebGL xterm.js PTY bridge (`@app.websocket("/api/pty")`). Never re-implement the chat transcript/composer in React.

### Desktop App (`apps/desktop/`)
Electron + React + nanostores (`@assistant-ui/react`) talking to a headless `hermes serve` backend over JSON-RPC (`requestGateway(method, params)`).
- **Curated Slash Commands (`apps/desktop/src/lib/desktop-slash-commands.ts`)**: `isDesktopSlashCommand` gates execution; `isDesktopSlashSuggestion` gates palette completion; `isDesktopSlashExtensionCommand` ensures user skills and quick commands pass through to completion menus.

---

## 7. Tool Registration & Creation Standards

Core tools require 2 files:

1. **Create `tools/your_tool.py`**:
```python
import json, os
from tools.registry import registry

def check_requirements() -> bool:
    return bool(os.getenv("EXAMPLE_API_KEY"))

def example_tool(param: str, task_id: str = None) -> str:
    return json.dumps({"success": True, "data": "..."})

registry.register(
    name="example_tool",
    toolset="example",
    schema={
        "name": "example_tool",
        "description": "Example tool description. State path: display_hermes_home()",
        "parameters": {
            "type": "object",
            "properties": {"param": {"type": "string"}},
            "required": ["param"],
        },
    },
    handler=lambda args, **kw: example_tool(param=args.get("param", ""), task_id=kw.get("task_id")),
    check_fn=check_requirements,
    requires_env=["EXAMPLE_API_KEY"],
)
```

2. **Wire in `toolsets.py`**: Add tool name to `_HERMES_CORE_TOOLS` or a named toolset in `TOOLSETS`.

### Invariants for Tools
- Handlers MUST return a JSON string.
- Descriptions referencing paths MUST use `display_hermes_home()`.
- State storage MUST use `get_hermes_home()` (never hardcode `~/.hermes`).
- Agent-level tools (`todo`, `memory`) are intercepted by `run_agent.py` before `handle_function_call()`.
- Never hardcode other tool names in schemas (causes hallucinations when target toolset is disabled); inject dynamically in `model_tools.py:get_tool_definitions()`.

---

## 8. Dependency Pinning & Configuration Management

### Exact Pinning Policy (Supply Chain Hardening)
- Core dependencies in `pyproject.toml` are pinned to `>=floor,<next_major` or exact pins (`==X.Y.Z`).
- Git URLs and GitHub Actions MUST use full 40-character commit SHAs.
- Run `uv lock` to update `uv.lock` with hashes whenever modifying dependencies.

### Configuration Architecture
- **`config.yaml`**: All non-secret settings. Add defaults to `DEFAULT_CONFIG` in `hermes_cli/config.py`. Bump `_config_version` only for breaking structure migrations.
- **`.env`**: Secrets ONLY (API keys, tokens). Register in `OPTIONAL_ENV_VARS` in `hermes_cli/config.py`.
- **Loaders**:
  - `load_cli_config()` (`cli.py`): CLI mode (defaults + user YAML).
  - `load_config()` (`hermes_cli/config.py`): CLI subcommands (`hermes tools`, `hermes setup`).
  - Direct YAML load (`gateway/run.py`): Gateway runtime.
- **Working Directory**: CLI uses `os.getcwd()`. Messaging uses `terminal.cwd` from `config.yaml` (bridged to `TERMINAL_CWD`).

---

## 9. Plugin System

Discovered from `~/.hermes/plugins/`, `./.hermes/plugins/`, and pip entry points.

### General Plugins (`plugins/<name>/`)
- Entry point `register(ctx)` registers tools (`ctx.register_tool`), CLI subcommands (`ctx.register_cli_command`), and lifecycle hooks (`pre_tool_call`, `post_tool_call`, `pre_llm_call`, `post_llm_call`, `on_session_start`, `on_session_end`).
- Additive contract: Hook callbacks use signature inspection so narrow callbacks receive only declared args while `**kwargs` receive full payloads. Deprecations require a warning and 2 minor releases notice.

### Plugin Storage Isolation (`plugins/plugin_storage.py`)
- Plugins store state in `<hermes_home>/plugin-data/<plugin_name>/`.
- Use `plugin_data_dir(name)` for isolated paths and `plugin_db(name, filename)` for WAL-enabled SQLite connections.

### Memory-Provider Plugins (`plugins/memory/<name>/`)
- Implements `MemoryProvider` ABC (`agent/memory_provider.py`), orchestrated by `agent/memory_manager.py`.
- Discovery is bundled-first (prevents drop-in shadowing). Activated via `memory.provider` in `config.yaml`.
- Built-ins include `honcho`, `mem0`, `supermemory`, `byterover`, `hindsight`, `lmcache`.
- *Policy*: In-tree list is closed; new memory backends must ship as standalone external plugins.

### Model-Provider Plugins (`plugins/model-providers/<name>/`)
- Calls `providers.register_provider(ProviderProfile(...))` at load time. Scanned lazily on first access.
- User plugins in `$HERMES_HOME/plugins/model-providers/` override bundled ones (last-writer-wins).

---

## 10. Skill Authoring Standards (Hardline)

Every bundled or contributed skill MUST adhere to these rules:
1. **`description` ≤ 60 characters**: Single sentence, ends with a period, describes capability without marketing fluff ("powerful", "advanced").
2. **Reference native tools in prose**: Point to Hermes tools in backticks (`` `terminal` ``, `` `read_file` ``, `` `patch` ``, `` `search_files` ``, `` `vision_analyze` ``), never raw shell utilities (`grep`, `cat`, `sed`).
3. **Platform gating**: Audit imports for POSIX primitives (`fcntl`, `os.kill(0)`, `/tmp`). Use cross-platform fallbacks (`pathlib`, `psutil`) or declare `platforms: [macos]`.
4. **Author credit**: Real contributor name + handle first; Hermes Agent secondary.
5. **Modern section structure**: `# <Skill> Skill` → Intro → `## When to Use` → `## Prerequisites` → `## How to Run` → `## Quick Reference` → `## Procedure` → `## Pitfalls` → `## Verification`.
6. **File separation**: Helpers in `scripts/`, templates in `templates/`, reference docs in `references/`.
7. **Tests**: `tests/skills/test_<skill>_skill.py` using stdlib + pytest + mocks (no live network calls).

---

## 11. Subsystems: Delegation, Curator, Cron, Kanban

### Delegation (`tools/delegate_tool.py`)
- Spawns subagents with isolated context and terminal sessions. Accepts `goal` (single) or `tasks: [...]` (batch concurrent).
- `role="leaf"` (default worker: cannot delegate, use memory, or send messages) vs. `role="orchestrator"` (can spawn workers up to `delegation.max_spawn_depth`).
- Background delegation (`background=true`) returns a task ID immediately and re-enters via the completion queue.

### Curator (`agent/curator.py`)
- Background skill lifecycle management for agent-created skills (`created_by: "agent"`). Tracks usage in `~/.hermes/skills/.usage.json` and auto-archives stale skills to `~/.hermes/skills/.archive/` (never deletes). Pinned skills (`hermes curator pin <name>`) are exempt from review.

### Cron (`cron/jobs.py` + `cron/scheduler.py`)
- Schedules jobs via `cronjob` tool or `hermes cron`. Supports durations (`"30m"`), natural phrases (`"every 2h"`), 5-field cron expressions (`"0 9 * * *"`), or ISO timestamps.
- Enforces a **3-minute hard interrupt**, file locking (`~/.hermes/cron/.tick.lock`), and delivery in isolated session frames to preserve user role alternation.

### Kanban Work Queue (`plugins/kanban/` + `tools/kanban_tools.py`)
- Multi-agent collaboration board. Dispatcher runs inside gateway (`kanban.dispatch_in_gateway: true`) to claim ready tasks and spawn worker profiles. Board is a hard boundary (`HERMES_KANBAN_BOARD`). Auto-blocks tasks after consecutive failure limits.

---

## 12. Critical Policies & Known Pitfalls

### Profile Isolation & Path Rules
- **Always use `get_hermes_home()`** from `hermes_constants`. Never hardcode `~/.hermes` or `Path.home() / ".hermes"` (breaks profile isolation).
- **Use `display_hermes_home()`** for user-facing output messages.
- **Gateway multiplex secret scope**: Read secrets via `_get_scoped_secret()`. A miss under multiplexing MUST return default, NEVER fall through to `os.environ` (leaks other profiles' credentials and authorization allowlists).

### Streaming Delivery Contract (Relay / Slack)
- **Draft frames must be prefix-stable**: Frame N must be an exact string prefix of frame N+1 (no fence auto-closing or per-tick conversions; prevents stacked copy duplicates).
- **Consumer declares final**: Augmentations ride `finish(final_text)`.
- **Interim sends**: Set `metadata["_interim_send"] = True` on commentary sends.
- **Reconcile by edit**: Edit existing message ID; plain send is fallback only.

### Gateway Message Guards
Messages pass through (1) base adapter queue and (2) gateway runner interceptor. Control commands (`/stop`, `/new`, `/approve`, `/deny`) MUST bypass both guards inline.

### Curses Pickers & ANSI Codes
- All interactive CLI pickers MUST use `hermes_cli/curses_ui.py`.
- Never use `\033[K` in spinner code (leaks under prompt_toolkit). Use space-padding `f"\r{line}{' ' * pad}"`.

---

## 13. Testing Discipline & CI Parity

### Parity Test Runner (`scripts/run_tests.sh`)
Always run tests via `scripts/run_tests.sh` (or `python -m pytest` with CI flags). Parity runner enforces:
- Fresh subprocess per test file (`scripts/run_tests_parallel.py`) to prevent module-level state leaks.
- Isolated temporary `HERMES_HOME`.
- UTC timezone, `LANG=C.UTF-8`, and unset provider credentials.
- Auto-retries flaky test files once (`--file-retries=1`). Any flaky test is treated as a bug to fix.

### Test Placement
- Tests checking `package.json`, `tsconfig.json`, or `.ts`/`.tsx` files belong in the JS test suite (`vitest`), not `tests/*.py` (prevents CI change-classifier mismatches).

### Operating System Testing
- Use explicit markers: `@pytest.mark.linux_only`, `@pytest.mark.macos_only`, `@pytest.mark.windows_only`. Never mock `sys.platform` or use bare `skipif(sys.platform != ...)` (causes test selection drops in CI).

### Banned Testing Antipatterns
- **No change-detector tests**: Never assert snapshots of mutable data (`assert len(_PROVIDER_MODELS) == 8` or exact version literals). Test invariants and relationships instead.
- **Never read source code in tests**: Banned outright. Do not regex `.py` or `.ts` files to test implementation shape; extract small pure functions and test runtime inputs/outputs.
- **Never write to `~/.hermes/`**: Always monkeypatch `HERMES_HOME` to `tmp_path`.

---

## 14. Fork Overlay & Local Workspace Policies

- **Fork Overlay (`fork/`)**: Fork-specific ops, harness, and extensions live under `fork/` and `scripts/windows/`. Upstream merges reapply verified fork advantages on a clean upstream base via `scripts/merge_tools/` / `scripts/sync_all.py`.
- **Root Layout**: Packaging and entry modules (`run_agent.py`, `cli.py`, `model_tools.py`), `scripts/`, `docs/`, and `tests/` remain at root.
- **Local Scratch**: Temporary probes go to `tmp/probes/` (gitignored). Implementation logs go to `_docs/`. Never commit `.env`, credentials, or release build artifacts.

---

## 15. Learned User Preferences & Workspace Facts

- **Hermes Restart Protocol**: Rebuild desktop (`hermes desktop --build-only --force-build`) + Llama hot-standby (`-StartLlama`). Never launch from `.worktrees/`.
- **Desktop Launch Target**: Canonical packaged `apps/desktop/release/win-unpacked/Hermes.exe`.
- **`HERMES_DESKTOP_HERMES_ROOT`**: Points exclusively to the canonical repository root (`c:\Users\downl\Documents\New project\hermes-agent`).
- **PR & Remote Rules**: Upstream PRs in King's English without `_docs/` or fork features. `origin` = `zapabob/hermes-agent`, `upstream` = `NousResearch/hermes-agent`.
- **Local Llama Supercharger**: Configured context length up to 131,072 tokens.
- **Desktop Wallpaper Themes**: Any `background_image` configuration requires high-contrast chat bubble overlays for readability.
- **MILSPEC Standards**: Print is strictly forbidden (`logging` only). UTF-8 fixed encoding. All changes documented in `_docs/yyyy-mm-dd_<feature>_<agent>.md`.
