# LMCache Integration Investigation (2026-08-21)

## Session Summary

User requested integration review of LMCache (https://github.com/zapabob/LMCache.git) as a Hermes Agent plugin. Key findings:

### LMCache Status
- **Independent project**, NOT currently integrated as Hermes plugin
- Has its own `AGENTS.md` (human-owned, agents must not modify)
- Has `pyproject.toml` with `torch==2.13.0` build requirement
- Standalone test suite (pytest markers, CI configuration)
- Git remote already configured as `lmcache` in hermes-agent

### Hermes Agent Plugin System (at time of investigation)
- **72 plugin directories** in `plugins/`
- Established patterns via `plugins/plugin_storage.py` for durable state
- Plugin storage at `<hermes_home>/plugin-data/<name>/` (survives update/remove)
- Example plugins: `hermes-achievements`, `hermes-bot-mode`, `lm-twitterer`

### Investigation Methods Used
1. `git remote -v` — confirmed `lmcache` remote exists
2. `git clone --depth 1` — fetched LMCache repo to `/tmp/`
3. `cat AGENTS.md` — read LMCache's human-owned policy
4. `ls plugins/` — enumerated Hermes plugins
5. `cat plugins/plugin_storage.py` — found storage convention
6. `find . -name "*.py"` — searched for LMCache references (none)
7. `skills_list` — checked existing skill categories

### Integration Assessment
- **Footprint ladder position:** Plugin rung (4 of 6)
- **Why plugin not core:** LMCache has independent repo, AGENTS.md, test suite, build deps
- **Practical path:** Invoke via `execute_code` or custom skill, not as built-in plugin
- **Storage recommendation:** Use `plugin_data_dir("lmcache")` if any durable state needed

### Files Created in This Session
- `skills/software-development/hermes-plugin-integration/SKILL.md` — class-level integration guide
- `skills/software-development/hermes-plugin-integration/references/LMCache-investigation-2026-08-21.md` — session detail

### Related Hermès Concepts
- **Per-conversation prompt caching is sacred** — this skill doc should not mutate conversation context
- **Narrow waist; capability at the edges** — plugin fits edges, not core waist
- **Footprint ladder** — plugin rung chosen over core tool