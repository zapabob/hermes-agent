# Fork invariants

1. The frozen upstream input is immutable and commits newer than the recorded
   snapshot are out of scope.
2. Official stable and public APIs are the preferred integration boundary.
3. Verified downstream features are preserved until replacement parity is
   demonstrated by code and tests.
4. Windows 11 native remains Tier 1 independently of upstream priorities.
5. The external Go watchdog at `scripts/windows/watchdog-go` is the only outer
   automatic restart authority. Other services may report health or request a
   restart but may not form recovery loops.
6. Hermes core retains the sole session, approval, profile, gateway ownership,
   model-catalogue, and tool-registry authorities.
7. Prompt-cache prefixes, message-role alternation, profile isolation, and
   credential boundaries must not regress.
8. Plugin discovery entrypoints remain where official discovery expects them;
   shared fork implementation may move behind downstream-owned modules.
9. State paths use official profile-aware Hermes path functions. User-visible
   paths use the official display helper.
10. Destructive and update operations are deterministic, auditable, and
    recoverable. Local, CI, runtime, and restart-durability evidence are
    reported separately.
