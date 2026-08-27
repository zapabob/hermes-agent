"""``hermes security`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

from typing import Callable


def build_security_parser(subparsers, *, cmd_security: Callable) -> None:
    """Attach the ``security`` subcommand to ``subparsers``."""
    # =========================================================================
    security_parser = subparsers.add_parser(
        "security",
        help="Supply-chain audit and Windows workstation malware protection",
        description=(
            "Run the existing OSV.dev supply-chain audit or manage local Windows "
            "malware scanning, definition state, monitoring, and encrypted quarantine."
        ),
    )
    security_subparsers = security_parser.add_subparsers(
        dest="security_command",
        metavar="<subcommand>",
    )

    audit_parser = security_subparsers.add_parser(
        "audit",
        help="Run a one-shot supply-chain audit",
        description="Query OSV.dev for known vulnerabilities in installed components.",
    )
    audit_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human-readable text",
    )
    audit_parser.add_argument(
        "--fail-on",
        default="critical",
        choices=["low", "moderate", "high", "critical"],
        help="Exit non-zero when any finding meets this severity (default: critical)",
    )
    audit_parser.add_argument(
        "--skip-venv",
        action="store_true",
        help="Skip scanning the Hermes Python venv",
    )
    audit_parser.add_argument(
        "--skip-plugins",
        action="store_true",
        help="Skip scanning plugin requirements files",
    )
    audit_parser.add_argument(
        "--skip-mcp",
        action="store_true",
        help="Skip scanning pinned MCP servers in config.yaml",
    )
    audit_parser.set_defaults(func=cmd_security)

    status_parser = security_subparsers.add_parser("status", help="Show local scanner, feed, watcher, and quarantine status")
    status_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    status_parser.set_defaults(func=cmd_security)

    scan_parser = security_subparsers.add_parser("scan", help="Scan a file, directory, or workstation scope")
    scope = scan_parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("path", nargs="?", help="File or directory to scan")
    scope.add_argument("--quick", action="store_true", help="Scan common user-space risk locations")
    scope.add_argument("--full", action="store_true", help="Scan all local drive roots")
    scan_parser.add_argument("--no-quarantine", action="store_true", help="Report detections without quarantining")
    scan_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    scan_parser.set_defaults(func=cmd_security)

    update_parser = security_subparsers.add_parser("update", help="Update and validate local security definitions")
    update_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    update_parser.set_defaults(func=cmd_security)

    feeds_parser = security_subparsers.add_parser("feeds", help="List installed feed versions and state")
    feeds_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    feeds_parser.set_defaults(func=cmd_security)

    watch_parser = security_subparsers.add_parser("watch", help="Manage bounded user-space file monitoring")
    watch_subparsers = watch_parser.add_subparsers(dest="watch_command", required=True)
    for name in ("status", "enable", "disable"):
        child = watch_subparsers.add_parser(name)
        child.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
        child.set_defaults(func=cmd_security)

    quarantine_parser = security_subparsers.add_parser("quarantine", help="Manage encrypted quarantine items")
    quarantine_subparsers = quarantine_parser.add_subparsers(dest="quarantine_command", required=True)
    quarantine_list = quarantine_subparsers.add_parser("list")
    quarantine_list.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    quarantine_list.set_defaults(func=cmd_security)
    quarantine_inspect = quarantine_subparsers.add_parser("inspect")
    quarantine_inspect.add_argument("item_id")
    quarantine_inspect.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    quarantine_inspect.set_defaults(func=cmd_security)
    quarantine_restore = quarantine_subparsers.add_parser("restore")
    quarantine_restore.add_argument("item_id")
    quarantine_restore.add_argument("--destination")
    quarantine_restore.add_argument("--force", action="store_true", help="Restore even when current signatures still detect it")
    quarantine_restore.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    quarantine_restore.set_defaults(func=cmd_security)
    quarantine_delete = quarantine_subparsers.add_parser("delete")
    quarantine_delete.add_argument("item_id")
    quarantine_delete.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    quarantine_delete.set_defaults(func=cmd_security)
    security_parser.set_defaults(func=cmd_security)
