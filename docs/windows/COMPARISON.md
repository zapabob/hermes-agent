# Distribution comparison

This document explains the downstream distribution without making unsupported
negative claims about the official project.

| Capability | Official Hermes | Windows Workstation Edition | Evidence |
| --- | --- | --- | --- |
| Hermes public APIs | Authoritative upstream contracts | Preserved and contract-tested | `tests/downstream/test_upstream_api_contracts.py` |
| Native Windows CI | See upstream policy / not asserted here | Tier-1 jobs run on `windows-latest` | `.github/workflows/fork-cicd.yml` |
| Release baseline | See upstream policy / not asserted here | Exact frozen and qualified upstream SHA | `.codex/UPSTREAM_SNAPSHOT.json` |
| Windows path/process qualification | See upstream policy / not asserted here | Drive, MSYS/WSL alias, NTFS, process and IPC contracts | `tests/downstream/test_windows_contracts.py` |
| External Go watchdog | See upstream policy / not asserted here | Separate Desktop/backend and embedding supervisor | `scripts/windows/watchdog-go/*_test.go` |
| Local llama/GGUF lifecycle | Official provider contracts are authoritative | Windows launcher, fallback, hot-swap and health contracts | `tests/hermes_cli/test_llama_fallback_runtime.py` |
| Local embedding supervision | Official memory/provider seams are authoritative | Optional loopback embedding recovery through the Go watchdog | `scripts/windows/watchdog-go/embedding_test.go` |
| Consumer NVIDIA workstation target | See upstream policy / not asserted here | Windows 11 x64 and consumer NVIDIA evidence contract | `scripts/windows/Get-HermesWorkstationQualification.ps1` |
| VRChat/Unity integrations | Official plugin registry is authoritative | Downstream plugins through official seams | `tests/plugins/test_vrchat_autonomy_plugin.py` |
| Local voice stack | Official TTS contracts are authoritative | Irodori, VOICEVOX, and local TTS routes | `tests/plugins/test_irodori_tts_plugin.py` |
| Semantic/cognitive memory | Official memory-provider interface is authoritative | Semantic Graph and Ebbinghaus extensions | `tests/plugins/test_semantic_graph_registration.py` |
| Release manifest | See upstream policy / not asserted here | Deterministic identity, hashes, channels, qualification, signing | `scripts/downstream/generate_release_manifest.py` |
| Windows install E2E | See upstream policy / not asserted here | Non-admin path-with-spaces installer, portable, and upgrade tests | `scripts/windows/Test-HermesInstallerE2E.ps1` |

The downstream does not replace Nous Research Hermes. Operators who prefer the
official release cadence and support model should use
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).
