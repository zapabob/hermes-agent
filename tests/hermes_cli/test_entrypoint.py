"""Entry-point wiring: ``python -m hermes_cli`` matches the ``hermes`` script."""

import importlib.util
import subprocess
import sys
from pathlib import Path


def test_hermes_cli_main_module_spec_exists():
    """Package exposes __main__ so ``python -m hermes_cli`` works."""
    spec = importlib.util.find_spec("hermes_cli.__main__")
    assert spec is not None


def test_py_m_hermes_cli_version_exits_zero():
    """Smoke: module invocation reaches argparse and exits on --version."""
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "-m", "hermes_cli", "--version"],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0
    assert "Hermes" in proc.stdout or "hermes" in proc.stdout.lower()
