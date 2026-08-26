# Hermes Agent Windows Workstation Edition

<p align="right">
  <a href="README.md"><kbd>English</kbd></a>
  <a href="README.ja.md"><kbd>日本語</kbd></a>
  <a href="README.zh-CN.md"><kbd>简体中文</kbd></a>
</p>

> [!NOTE]
> `README.md` is the canonical English document. The Japanese and Simplified Chinese translations follow this file.

Windows-first downstream distribution of Hermes Agent.

This is an unofficial downstream distribution.
It is not affiliated with or endorsed by Nous Research.
Original Hermes Agent is developed by Nous Research and licensed under MIT.

[![Windows Workstation Tier-1 CI](https://github.com/zapabob/hermes-agent-windows/actions/workflows/fork-cicd.yml/badge.svg)](https://github.com/zapabob/hermes-agent-windows/actions/workflows/fork-cicd.yml)

## 1. Product identity

Hermes Agent Windows Workstation Edition is a feature-rich Windows-first
downstream distribution for persistent local AI workstations. It retains the
Hermes CLI command, public contracts, plugin model, and upstream history while
maintaining an explicit downstream policy for native Windows operation, local
models, memory, voice, VR/Unity, and recovery.

The product ledger is [FEATURES.yaml](FEATURES.yaml). Direct patches carried in
upstream-owned files are tracked separately in [CARRY.yaml](CARRY.yaml).

## 2. Windows-first goals

The primary target is Windows 11 x64 with native Python, native Node/Electron,
an interactive desktop, and a consumer NVIDIA GPU. The design supports
continuous operation with local LLM and embedding services, voice services,
VRChat/Unity integrations, and remote management.

Windows is a Tier-1 target independently of upstream platform priorities.
Native behavior is tested on `windows-latest`; Linux cross-compilation is not
accepted as Windows runtime evidence.

## 3. Who this is for

This distribution is intended for operators and developers who maintain a
Windows AI workstation and need source-level control over local inference,
long-lived services, memory, desktop behavior, and recovery. It assumes comfort
with PowerShell, Git, Python environments, Node tooling, and reading CI results.

For the simplest official Hermes installation and the upstream support model,
use the original project linked in section 15.

## 4. Downstream advantages

The downstream adds native Windows runtime and recovery contracts, an external
Go watchdog, local llama.cpp/GGUF and embedding lifecycles, local secretary and
provider integrations, semantic and cognitive memory extensions, VRChat/Unity
and local voice routes, OSINT/Shinka extensions, Desktop Git/review surfaces,
and additional security and provider-fallback coverage.

These capabilities compose with official Hermes APIs. The fork does not create
parallel session, approval, profile, gateway, model-catalogue, or tool-registry
authorities.

## 5. Verified feature matrix

| Area | Verified implementation | Contract evidence |
| --- | --- | --- |
| Windows runtime | Native path, process, IPC, NTFS handoff, terminal, credentials, power and GPU helpers | `tests/downstream/test_windows_contracts.py` |
| Recovery | External Go watchdog and watchdog-managed Desktop backend | `scripts/windows/watchdog-go/*_test.go` |
| Local inference | llama.cpp/GGUF fallback and hot-swap scripts | `tests/hermes_cli/test_llama_fallback_runtime.py` |
| Local embeddings | Watchdog embedding lifecycle and semantic graph backends | `scripts/windows/watchdog-go/embedding_test.go` |
| Local secretary | Read/write action separation over official agent boundaries | `tests/downstream/test_upstream_api_contracts.py` |
| Providers | Hypura/local provider integration and provider rotation/fallbacks | `tests/fork/test_hypura_oai_proxy.py` |
| Memory | Semantic Graph hybrid retrieval and Ebbinghaus cognitive extensions | `tests/plugins/test_semantic_graph_registration.py` |
| VR and Unity | VRChat autonomy tooling and Unity bridge | `tests/plugins/test_vrchat_autonomy_plugin.py` |
| Voice | Irodori, VOICEVOX, and local TTS routes | `tests/plugins/test_irodori_tts_plugin.py` |
| AITuber | AITuber OnAir and AITuber Kit plugins | `tests/plugins/test_aituber_onair_plugin.py` |
| OSINT/Shinka | Shinka, SitDeck, WorldMonitor, and OSINT plugin surfaces | `tests/plugins/test_shinka_osint_plugin.py` |
| Desktop | Git/review extensions through official Desktop IPC and pane contracts | `apps/desktop/electron/git-review-ops.test.ts` |
| Security | Security guidance plus hardened approval and execution boundaries | `tests/plugins/test_security_guidance_plugin.py` |

The complete per-feature owner, public surface, upstream overlap, Windows
requirement, tests, and integration policy are recorded in `FEATURES.yaml`.

## 6. Windows Tier-1 support contract

Tier-1 coverage includes native drive paths, MSYS `/c/...` and supported WSL
`/mnt/c/...` aliases, NTFS locks, locked executable and extension-module
updates, process trees, applicable Job Object behavior, PowerShell quoting, Git
Bash boundaries, CP932/UTF-8 boundaries, CRLF, venv `Scripts\`, and Electron
stdio pipes.

Runtime qualification covers sleep/resume, network and loopback-provider
recovery, Desktop relaunch, updater handoff, watchdog recovery, llama restart
and hot-swap, embedding restart, and profile/session persistence. The normative
contract is [.codex/WINDOWS_PLATFORM_CONTRACT.md](.codex/WINDOWS_PLATFORM_CONTRACT.md).

## 7. Local AI architecture

Official Hermes provider and model-catalogue contracts remain authoritative.
Downstream local runtimes connect through those contracts: llama.cpp/GGUF via
the local fallback runtime, Hypura through the provider plugin seam, and local
embeddings through Semantic Graph backends and the watchdog-managed loopback
service.

Operator scripts remain under `scripts/windows/`. Runtime plugin entrypoints
remain under `plugins/` so official discovery continues to work.

## 8. Watchdog and recovery architecture

`scripts/windows/watchdog-go` is the sole outer automatic restart authority. It
can supervise the packaged Desktop, publish the prewarmed backend manifest, and
coordinate the configured local embedding process. Desktop, backend, llama,
and embedding components may expose health or request recovery, but they do not
form independent automatic restart loops.

The downstream Python service modules are side-effect-free contracts. Actual
operator startup and deployment remain in the PowerShell and Go surfaces under
`scripts/windows/`.

## 9. Memory and semantic retrieval

The Semantic Graph plugin provides graph storage, hybrid retrieval, embeddings,
fusion, abstention, and cognitive helpers through official plugin and memory
interfaces. The Ebbinghaus provider adds experience and retention policies and
can bridge to Semantic Graph. Both retain isolated plugin entrypoints and
focused test suites.

## 10. VRChat, Unity, and voice integrations

VRChat autonomy tools, observation and relay helpers, the Unity bridge package,
VOICEVOX, Irodori, and other local TTS routes remain downstream-owned features.
They use official plugin, tool, and TTS contracts rather than modifying the core
into a VR- or voice-specific runtime.

External publishing and write actions remain approval-gated. Local generation
does not imply authorization to publish or mutate an external account.

## 11. Installation

There is currently no verified fork-specific binary installer advertised by
this repository. Install from source in PowerShell:

```powershell
git clone https://github.com/zapabob/hermes-agent-windows.git
Set-Location hermes-agent-windows
uv sync --all-extras
uv run hermes --help
uv run hermes setup
```

For Desktop development and a source build:

```powershell
npm ci
npm --workspace apps/desktop run typecheck
npm --workspace apps/desktop run build
```

Review configuration before enabling any 24/7 service or Scheduled Task. API
keys and tokens belong in the profile-scoped Hermes secret store or `.env` as
documented by Hermes; non-secret settings belong in `config.yaml`.

## 12. Update and upstream integration policy

Upstream is an integration input, not the downstream product authority. Each
campaign freezes an exact SHA in `.codex/UPSTREAM_SNAPSHOT.json`, classifies its
commits in `UPSTREAM_ADOPTION.yaml`, and records direct carry in `CARRY.yaml`.
`scripts/upstream/snapshot_sync.py` accepts an explicit SHA and never resolves a
moving latest branch.

Official public APIs are preferred. Security and data-integrity fixes are
composed with stronger verified downstream properties. A downstream feature is
not removed merely because upstream adds a similar name; replacement requires
parity evidence.

## 13. Architecture

Fork-owned Python boundaries live under `downstream/`: `compat/hermes` delegates
to official contracts, `platform/windows` owns native policy, `services` defines
long-lived service contracts, and `features` validates the product ledger.
There is deliberately no top-level Python package named `platform`.

Core Hermes remains the narrow waist. Plugins and skills hold capabilities,
profile-aware official path helpers own state paths, and prompt-cache and
message-role invariants remain mandatory.

## 14. Security

Do not commit secrets, personal runtime data, profile databases, model files,
local artifacts, or generated credentials. Keep write, publish, destructive,
and shell actions behind explicit approval. Child service environments should
project only required variables rather than inherit ambient credentials.

Security gates check the locked Python graph, Python advisories, production npm
advisories, Go module integrity, OSV results, supply-chain policies, and the
repository's security regression tests. A green local unit test is not a
substitute for exact-head CI or live runtime evidence.

## 15. Upstream project

Original Hermes Agent is maintained by Nous Research:
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).

The official upstream installer, website, documentation, issue tracker, and
support channels apply to the upstream distribution. They do not install or
endorse this downstream repository.

## 16. License and attribution

This downstream remains licensed under the repository's MIT License. Original
Hermes Agent copyright and contributor history are preserved. Downstream work
is maintained independently by the fork contributors; upstream and downstream
issues, releases, and product claims must remain clearly distinguished.
