"""Names reserved for built-in Hermes CLI subcommands.

This module deliberately has no imports from the CLI bootstrap or plugin
loader. Both paths need the same collision boundary, and keeping it here
prevents a plugin registration check from introducing an import cycle.
"""

# Keep this in sync with the ``subparsers.add_parser("NAME", ...)`` calls in
# ``hermes_cli.main.main``. Missing an entry only costs a one-time discovery;
# an extra entry would let a plugin command silently fail to parse.
BUILTIN_SUBCOMMANDS = frozenset(
    {
        "acp", "approvals", "auth", "backup", "bundles", "checkpoints", "claw", "completion",
        "computer-use",
        "config", "console", "cron", "curator", "dashboard", "serve", "debug", "doctor",
        "dump", "egress", "fallback", "gateway", "hooks", "import", "import-agent", "insights",
        "gui", "desktop", "harness", "kanban", "login", "logout", "logs", "lsp", "mcp", "memory", "migrate", "moa",
        "journey", "memory-graph", "learning",
        "model", "monitoring", "pairing", "pause", "pets", "plugins", "portal", "profile",
        "project", "proxy",
        "prompt-size",
        "resume",
        "send", "sessions", "setup",
        "skin", "skills", "slack", "status", "sync", "tools", "uninstall", "update",
        "version", "webhook", "whatsapp", "whatsapp-cloud", "chat", "secrets", "security",
        "verify",
        # Help-ish invocations — plugin commands not being listed in
        # top-level --help is an acceptable trade-off for skipping an
        # expensive eager import of every bundled plugin module.
        "help",
    }
)
