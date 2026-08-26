# Windows Tier-1 platform contract

Windows 11 x64 with native Python, native Node/Electron, an interactive desktop,
and a consumer NVIDIA GPU is a Tier-1 downstream target. The workstation may
operate continuously with local LLM, local embeddings, voice, VRChat/Unity, and
remote management services.

Required compatibility covers native drive paths, MSYS `/c/...` aliases, WSL
`/mnt/c/...` aliases where supported, NTFS sharing locks, locked executable and
extension-module updates, process-tree cleanup, applicable Job Object behavior,
PowerShell argument quoting, Git Bash boundaries, CP932/UTF-8 boundaries, CRLF,
venv `Scripts\` layout, and Electron stdio pipes.

Runtime qualification covers sleep/resume, network loss and recovery, loopback
provider loss and recovery, Desktop relaunch, updater handoff, watchdog
recovery, llama restart and hot-swap, embedding restart, and profile/session
persistence. Cross-platform code expected to work on Windows must run on a
native Windows CI host; a Linux cross-compile or a marker-only lane is not
sufficient evidence.

Windows policy belongs under `downstream/platform/windows`. Existing official
Hermes helpers remain authoritative when they already own a concept; downstream
helpers delegate to them rather than creating competing process, session,
approval, profile, or registry authorities.
