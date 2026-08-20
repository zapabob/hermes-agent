# PR #70 security/code-quality review

- Reviewed head: `refs/remotes/origin/pr-70` / `ae172bdcd0bf42895b337e0167cc79404116cf55`
- Base: `main` / `fe6acdca3258dc70b5997a4436a0a172e5e86da9`
- Recommendation: **REQUEST_CHANGES**
- codeQualityStatus: **BLOCK**
- Scope: backend skin wallpaper trust, authenticated media loading, Windows file URL/UNC handling, profile and registered-connection isolation

## CRITICAL

None found.

## HIGH

### H1 — A background connection can replace the active connection's wallpaper metadata, which is then read through a different authenticated backend

`gateway.ready` always calls `ingestBackendSkin(..., {apply: false})` without the `fromActiveSource()` check used by `skin.changed` (`apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/lifecycle.ts:23-27, 34-39`). The destination registry and apply guard are process-global and keyed only by the unscoped skin name (`apps/desktop/src/themes/backend-sync.ts:28, 39, 54-111`). Consequently, a background connection/profile advertising the same theme name can overwrite the active theme's wallpaper metadata even though the palette is not explicitly applied.

`Backdrop` then resolves that unscoped path through `resolveMediaDisplaySrc` (`apps/desktop/src/components/Backdrop.tsx:72-100`). The authenticated remote read consults the mutable current `$connection` only when the read runs, sends only its profile, and omits `HermesApiRequest.connectionId` (`apps/desktop/src/lib/desktop-fs.ts:42-44, 60-63, 102-109`). Thus the path supplied by source B can be read from source A, and a profile/connection switch during resolution can also redirect a previously supplied path. This violates the registered-connection authentication boundary and permits cross-source UI content injection plus an unintended file read on the active backend.

Required correction: carry an immutable `(connectionId, normalized profile)` scope with every backend skin; key the backend theme registry and `lastSynced` state by that scope; resolve the displayed theme only from the active scope. Bind the wallpaper read to that captured scope and pass both `connectionId` and `profile` to the Electron API request. Merely reading `$connection` later is insufficient. If background seeding is unnecessary, additionally gate `gateway.ready` on `fromActiveSource()`, but source-keyed state is still needed for correct switching and races.

Required tests: two registered gateways with the same profile and skin names but different wallpaper paths; background `gateway.ready` must not alter the active wallpaper or issue an FS request. Switching to B must request B's exact `(connectionId, profile)`. A delayed read followed by an A-to-B switch must not issue A's path against B or let the stale result repaint B. Cover same-host multi-profile and two-host same-profile-name cases.

### H2 — Automatically loaded UNC wallpaper paths can initiate SMB access and leak Windows credentials

The new trust check deliberately accepts UNC paths because `isFileMediaPath` matches `\\\\...` and every slash-prefixed path (`apps/desktop/src/lib/media.ts:76-78`), and `Backdrop` sends accepted paths to the file reader without a local-only check (`apps/desktop/src/components/Backdrop.tsx:78-100`). The Python resolver preserves absolute paths (`hermes_cli/skin_engine.py:852-857`). On Windows, resolving/statting a path such as `\\\\attacker\\share\\wall.png` in either Electron's local file reader or the gateway's `/api/fs/read-data-url` can perform an outbound SMB authentication attempt. HTTP wallpapers being rejected does not close this network path.

This is an automatic load triggered by backend skin metadata, with no user confirmation or network-share allowlist. A compromised backend event, malicious skin, or prompt/skill-authored skin can therefore turn presentation metadata into an SSRF/NTLM credential-exposure primitive on the Windows host performing the read.

Required correction: treat UNC and other network file forms as remote URLs for skin-wallpaper purposes and reject them before Electron IPC or backend REST is invoked. At minimum reject `\\\\host\\share`, `//host/share`, and `file://host/share` (allowing a host only if an explicit, user-controlled network-wallpaper policy is introduced). The same local-only validator must run at the renderer boundary and at the actual Electron/backend file-read boundary so a crafted event cannot bypass renderer policy.

Required tests: each UNC spelling above must produce no `readFileDataUrl`/`hermes:api` call; mixed slash, case, percent-encoded, and extended UNC forms must also fail closed. A Windows integration test should assert that no filesystem stat/open is attempted for a network root.

## MEDIUM

### M1 — Windows `file:` URLs are parsed with URL pathname semantics and lose their drive/host meaning

`filePathFromMediaPath` returns `decodeURIComponent(new URL(path).pathname)` (`apps/desktop/src/lib/media.ts:169-178`). A focused Node/Windows-path probe showed `file:///C:/Users/Bob/wall.png` becoming `/C:/Users/Bob/wall.png`, which `path.win32.resolve` maps to `C:\\C:\\Users\\Bob\\wall.png`; `file://server/share/wall.png` loses `server` and becomes `C:\\share\\wall.png`. This is both a correctness failure and an unsafe ambiguity adjacent to H2.

Use an OS-aware file-URL conversion at the trusted main/backend boundary, preserve drive letters exactly, and reject non-local authorities rather than silently discarding them. Add exact-value tests for `C:\\...`, `C:/...`, `file:///C:/...`, `file://localhost/C:/...`, and rejected remote authorities.

## LOW

None found.

## Skill-perspective check

The `remove-ai-slops` and `programming` perspectives were applied. The production change is direct and does not introduce needless abstraction, untyped escape hatches, or goal-unrelated parsing. The E2E test is a meaningful real Python-gateway-to-Electron happy-path test rather than a deletion-only, tautological, or constant-mirroring test. It does, however, omit the security invariants above; the missing tests matter because the happy path gives false confidence about source binding and Windows network paths. No separate skill-perspective violation beyond those findings was identified.

## Verification performed

The review used `git show`/`git diff` against the exact immutable refs above and traced the renderer through Electron's authenticated API routing and `/api/fs/read-data-url`. A focused Node probe confirmed the Windows path transformations stated in M1. No checkout, fetch, source edit, staging operation, commit, or full test run was performed. The review artifact is the only file created, as required by the reviewer contract.

## Blockers

H1 and H2 must be fixed and covered by the stated source-isolation and Windows network-path tests before approval.
