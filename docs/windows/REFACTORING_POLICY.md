# Semantic-Preserving Refactoring Policy

Hermes Agent Windows Workstation Edition does not treat source-tree parity with
`NousResearch/hermes-agent` as a project objective. That does **not** mean the
downstream should freeze its internal architecture.

This document defines an independent refactoring programme for the Windows-native
downstream: improve maintainability, modularity, testability, navigability and
agent-development cost whilst preserving externally observable semantics and the
Windows Tier-1 contracts.

> **Refactor independently; preserve behaviour deliberately; prove equivalence.**

Upstream architectural work may be studied as prior art, but source layout,
module boundaries and commit topology are not compatibility requirements.

## 1. Non-negotiable invariants

A refactor is acceptable only when all applicable behaviour remains semantically
equivalent unless a separate, explicitly documented product change owns the
difference.

The preservation boundary includes:

- public CLI commands, arguments, exit behaviour and configuration semantics;
- tool names, JSON schemas, tool-call/result contracts and error classes;
- provider, model-catalogue and plug-in discovery contracts;
- session, profile, gateway and approval semantics;
- persisted state, migrations, database schemas and file formats;
- security boundaries, credential scoping and fail-closed behaviour;
- prompt-cache and message-role invariants;
- Desktop IPC/RPC and renderer-facing contracts;
- Windows-native path, process, IPC, NTFS, PowerShell, Job Object and updater behaviour;
- watchdog/recovery ownership and long-lived-service lifecycle contracts;
- documented downstream compatibility surfaces in `FEATURES.yaml`, `CARRY.yaml` and
  `.codex/WINDOWS_PLATFORM_CONTRACT.md`.

Structural similarity to upstream is explicitly **not** an invariant.

## 2. Engineering principles

Refactoring work follows established software-engineering practice rather than
optimising for line-count reduction alone.

1. **Characterise before changing.** Add or identify tests that capture the current
   externally observable behaviour before structural edits.
2. **Prefer small, reviewable slices.** Use bounded subsystem changes with explicit
   ownership rather than whole-tree rewrites.
3. **Use single-responsibility boundaries.** Split oversized modules around stable
   responsibilities, not arbitrary line counts.
4. **Keep dependency direction explicit.** Core contracts must not depend on
   downstream UI, platform or integration details. Windows-specific policy belongs
   behind explicit seams.
5. **Compose instead of duplicating.** Consolidate repeated behaviour only when the
   shared abstraction has a stable semantic contract.
6. **Avoid speculative abstraction.** Do not introduce generic layers without at
   least two real consumers or a documented boundary requirement.
7. **Preserve public seams deliberately.** Compatibility shims must be explicit,
   tested and time-bounded where deprecation is intended.
8. **Measure the result.** Complexity, file/function size, import fan-out, test
   isolation, cold import cost and agent navigation/token cost may be tracked, but
   none overrides behavioural correctness.
9. **Treat Windows evidence as first-class.** Linux-only or synthetic success cannot
   certify Windows-native runtime behaviour.
10. **Use adversarial verification for security-sensitive structure.** Auth,
    credentials, approvals, sandboxing, remote execution, profile/session routing and
    update paths require focused negative tests.

## 3. Refactor acceptance contract

Each refactoring PR must state:

- **Scope:** the exact subsystem and files owned by the slice;
- **Behavioural contract:** what must remain unchanged;
- **Characterisation evidence:** tests or reproducible probes that describe the
  pre-refactor behaviour;
- **Structural objective:** what engineering debt is being reduced and why the chosen
  boundary is better;
- **Differential verification:** where practical, the same inputs are run against the
  pre- and post-refactor implementation and externally observable outputs compared;
- **Windows verification:** focused Windows-native tests for any platform-sensitive path;
- **Security verification:** negative and fail-closed cases when a trust or authority
  boundary is touched;
- **Performance check:** no material regression in startup, import or runtime hot paths
  without an explicit trade-off;
- **Exact-head CI:** the final PR head is green for the required lanes;
- **Provenance:** contributor authorship and salvage/cherry-pick credit remain intact
  where prior work is incorporated.

## 4. Differential-verification hierarchy

Use the strongest practical proof for each surface:

1. byte-for-byte equality where the surface is intentionally frozen, such as schemas,
   generated manifests, protocol payloads, SQL/DDL, config defaults and static prompt
   fragments;
2. structured semantic equality for serialised objects whose ordering or formatting is
   not normative;
3. behavioural differential tests for functions, RPCs, CLI commands and session
   transitions;
4. state-machine and property tests for lifecycle, recovery and authority-sensitive code;
5. real Windows runtime probes where operating-system behaviour is part of the contract.

A green unit suite alone is insufficient evidence for a large structural rewrite.

## 5. Initial candidate areas

Prioritise downstream areas where maintainability gain is high and the semantic
boundary can be tested precisely:

- oversized Windows, CLI and Desktop orchestration modules;
- process and subprocess lifecycle helpers;
- repeated Windows path, cwd and normalisation logic;
- Desktop/backend/watchdog lifecycle coordination;
- provider and local-runtime configuration shaping;
- plug-in discovery and registration helpers;
- repeated Git, updater and repository-normalisation logic;
- duplicated error and result normalisation;
- test harness utilities that currently duplicate production contract knowledge.

Do **not** begin by mechanically mirroring the current upstream module decomposition.

## 6. Campaign workflow

For each subsystem:

```text
characterise current semantics
        ↓
identify stable responsibilities and dependency direction
        ↓
extract one bounded slice
        ↓
run differential and invariant tests
        ↓
run Windows-native qualification where applicable
        ↓
measure complexity, navigation and import cost
        ↓
merge only at exact-head green
```

Large campaigns are a sequence of independently valid PRs. Every intermediate
commit and PR must leave the product in a supported state; no long-lived
half-migrated architecture.

## 7. Metrics

Track metrics as evidence, not goals:

- source LOC and code LOC;
- files over 2,000 and 5,000 lines;
- functions over 100 and 300 lines;
- cyclomatic complexity and nesting depth;
- import fan-out and circular-dependency count;
- cold import and startup time;
- focused test runtime;
- agent navigation cost and context tokens for representative maintenance tasks;
- Windows-specific regression count;
- carry-surface change relative to the frozen upstream snapshot.

A refactor that reduces LOC but weakens contracts, provenance, security,
readability or Windows behaviour is a regression.

## 8. Relationship with upstream

`NousResearch/hermes-agent` remains a reference upstream and a source of selected
security, protocol, compatibility and correctness fixes.

Architectural changes from upstream may be analysed and selectively reimplemented
when they improve this downstream, but they are adopted by **semantic value**, not
by source-tree parity.

Where upstream and downstream independently solve the same architectural problem,
preserve the downstream's stronger verified Windows properties and public
compatibility contracts.

## 9. Completion criteria

This programme is successful when:

- major downstream-owned and carried god-files are decomposed behind explicit contracts;
- no refactoring campaign requires continuous rebasing against upstream structure;
- Windows Tier-1 behaviour remains fully qualified;
- public Hermes-compatible contracts remain stable or have explicit versioned migrations;
- security-sensitive paths have permanent negative and regression coverage;
- refactoring reduces maintenance and agent-navigation cost measurably without
  behaviour drift;
- contributor provenance remains intact.

This is an **independent engineering programme**, not an upstream synchronisation
campaign.
