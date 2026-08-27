from __future__ import annotations

import argparse
import json
from pathlib import Path

from downstream.release_notes import build_release_notes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--previous-tag", default="")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    notes = build_release_notes(
        manifest,
        args.repo_root.resolve(),
        previous_tag=args.previous_tag or None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(notes, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
