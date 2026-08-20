# Follow-up Code Review: dependency and CI repair delta

## Verdict

- `codeQualityStatus`: WATCH
- `recommendation`: APPROVE
- Reviewed base: `0741ceb65b09e5a962b1dd491ad24227099e73db`
- Frozen official parent: `27562ad5f80e90f7d552f92dbd4af7f1f511c3c8`
- Scope: 12 modified tracked files plus restored `skills/autonomous-ai-agents/hermes-agent/references/native-mcp.md`

## CRITICAL

None.

## HIGH

None.

## MEDIUM

### Honcho prewarm conflict guard does not guard the associated cadence metadata

At `plugins/memory/honcho/__init__.py:570-574`, the new condition correctly prevents the generic startup prewarm from replacing an already queued query-aware `_prefetch_result`. However, `_last_dialectic_turn = 0` and `_dialectic_empty_streak = 0` remain unconditional after the lock. In the exact race described by the new comment, the retained query-aware result may therefore keep its payload while losing its corresponding cadence/failure metadata. That can make a later cadence decision behave as though the generic turn-0 prewarm won. No focused test currently constructs this interleaving; the existing Honcho suite passes but does not prove the new race contract.

This is non-blocking for this repair delta because the preferred query-aware payload is preserved, the normal turn path consumes pending results, and the effect is limited to scheduling/observability rather than API incompatibility or data loss. A focused follow-up should move all winning-result metadata updates into the same conditional critical section and add a deterministic interleaving test.

## LOW

None.

## Skill-perspective review

The `remove-ai-slops` and `programming` skills were loaded before judging tests and maintainability, together with the TypeScript and Python language guidance. The CI test edits are behavioral repairs rather than deletion-only, tautological, brittle prompt, or assertion-weakening tests: they patch the current shared keyless MCP API, explicitly select the OAuth branch under test, make random provider choice deterministic, and configure disposable Git identity. The fork-default test remains somewhat literal by design, but it verifies the distribution's official configuration API contract and fork extensions rather than mirroring an implementation-only helper. No HIGH-severity violation of either skill perspective was found.

## Evidence

- Merge parent contract: `HEAD^1=c5dff14d7ec59b00614ecbf2e8a2bf24769e7352`, `HEAD^2=27562ad5f80e90f7d552f92dbd4af7f1f511c3c8`.
- Restored official document: working blob and frozen official blob both equal `2d9133d8bffda71e9bc8c50386b6b54d9cef7fcb`.
- Independent focused tests: 171 passed in 36.28 seconds across the five changed CI test files plus Chat Completions and Honcho suites.
- Parent combined validation reported: 251 passed, 1 skipped; dependency lock checks and audits green.
- `uv lock --check`: passed, 253 packages resolved.
- `git diff --check`: passed.
- `package-lock.json`: valid JSON; both added Vite plugin entries use the same version, registry URL, and integrity.
- `pnpm-lock.yaml`: valid YAML; tar override is 7.5.22 and importer entries match the current desktop/bootstrap/TUI manifests for nanostores, blobatar, and driver.js.
- Secret-pattern review: no credential material. The two `sk-xxxxxxxx...` strings in restored `native-mcp.md` are placeholders in the byte-identical official document.
- Unrelated untracked paths `mini_llm_planner.py` and `results/` were excluded from review and must not be staged.

## Recommended exact staged paths

1. `agent/transports/chat_completions.py`
2. `package-lock.json`
3. `plugins/memory/honcho/__init__.py`
4. `pnpm-lock.yaml`
5. `pnpm-workspace.yaml`
6. `pyproject.toml`
7. `skills/autonomous-ai-agents/hermes-agent/references/native-mcp.md`
8. `tests/hermes_cli/test_fork_config_defaults.py`
9. `tests/hermes_cli/test_web_server_git.py`
10. `tests/plugins/web/test_parallel_keyless_mcp.py`
11. `tests/tools/test_mcp_oauth_redirect.py`
12. `tests/tools/test_web_providers_ddgs.py`
13. `uv.lock`

Do not stage `.omo/evidence/dependency-ci-repair-code-review.md`, `mini_llm_planner.py`, or anything under `results/`.

## Blockers

None.
