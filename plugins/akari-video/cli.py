from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from . import core
except ImportError:
    import core


def register_cli(subparser: argparse.ArgumentParser) -> None:
    subs = subparser.add_subparsers(dest="akari_video_command")
    status = subs.add_parser(
        "status", help="Show the pinned AKARI Video submodule status"
    )
    status.add_argument(
        "--detail", action="store_true", help="Include detailed submodule info"
    )
    subs.add_parser("skills", help="List the AKARI Video skills catalog")

    launch = subs.add_parser("launch", help="Launch the AKARI Video launcher")
    launch.add_argument(
        "args", nargs=argparse.REMAINDER, help="Arguments to pass to akari.mjs"
    )
    launch.add_argument("--project-dir", default="", help="Project directory to run in")


def _print(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok", True) else 1


def akari_video_command(args: argparse.Namespace) -> int:
    command = getattr(args, "akari_video_command", None)
    if command == "status":
        detail = getattr(args, "detail", False)
        return _print(json.loads(core.handle_status({"detail": detail})))
    if command == "skills":
        return _print(json.loads(core.handle_skills({})))
    if command == "launch":
        return _print(
            json.loads(
                core.handle_launch({
                    "project_dir": args.project_dir or None,
                    "args": args.args,
                })
            )
        )
    print("usage: hermes akari-video {status,skills,launch}")
    return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="akari-video")
    register_cli(parser)
    args = parser.parse_args()
    sys.exit(akari_video_command(args))
