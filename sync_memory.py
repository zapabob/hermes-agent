"""Compatibility import for the standalone memory synchronizer.

The root module is retained for callers that used the pre-move import path.
``run_sync`` is a small forwarding wrapper instead of a direct alias so the
historical ``sync_memory._export_obsidian`` monkeypatch seam continues to
control the implementation module during tests and integrations.
"""

from scripts.standalone import sync_memory as _impl

_latest_started_at = _impl._latest_started_at
_watermark_for_sources = _impl._watermark_for_sources
load_index = _impl.load_index
main = _impl.main
save_index = _impl.save_index
_export_obsidian = _impl._export_obsidian


def run_sync(*args, **kwargs):
    _impl._export_obsidian = _export_obsidian
    return _impl.run_sync(*args, **kwargs)

__all__ = [
    "_latest_started_at",
    "_export_obsidian",
    "_watermark_for_sources",
    "load_index",
    "main",
    "run_sync",
    "save_index",
]


if __name__ == "__main__":
    raise SystemExit(main())
