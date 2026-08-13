"""Tests for utils.atomic_json_write — crash-safe JSON file writes."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from utils import atomic_json_write, atomic_replace


class TestAtomicJsonWrite:
    """Core atomic write behavior."""







    def test_cleans_up_temp_file_on_baseexception(self, tmp_path):
        class SimulatedAbort(BaseException):
            pass

        target = tmp_path / "data.json"
        original = {"preserved": True}
        target.write_text(json.dumps(original), encoding="utf-8")

        with patch("utils.json.dump", side_effect=SimulatedAbort):
            with pytest.raises(SimulatedAbort):
                atomic_json_write(target, {"new": True})

        tmp_files = [f for f in tmp_path.iterdir() if ".tmp" in f.name]
        assert len(tmp_files) == 0
        assert json.loads(target.read_text(encoding="utf-8")) == original




    def test_mode_does_not_crash_without_fchmod(self, tmp_path):
        """Regression: os.fchmod is Unix-only and absent on Windows. Passing a
        mode must not raise AttributeError when fchmod is unavailable.

        Simulates the Windows os module by removing fchmod from the namespace.
        Previously this crashed in `hermes memory setup` while saving the
        Hindsight config with mode=0o600 (GitHub: Windows setup traceback).
        """
        import utils

        target = tmp_path / "secret.json"
        no_fchmod = {k: getattr(os, k) for k in dir(os) if k != "fchmod"}
        fake_os = type("FakeOs", (), no_fchmod)
        assert not hasattr(fake_os, "fchmod")

        with patch.object(utils, "os", fake_os):
            atomic_json_write(target, {"api_key": "secret"}, mode=0o600)

        assert json.loads(target.read_text(encoding="utf-8")) == {"api_key": "secret"}


    def test_atomic_replace_retries_transient_permission_error(self, tmp_path):
        import utils

        target = tmp_path / "data.json"
        tmp_file = tmp_path / "data.tmp"
        tmp_file.write_text('{"ok": true}', encoding="utf-8")
        calls = 0
        real_replace = os.replace

        def flaky_replace(src, dst):
            nonlocal calls
            calls += 1
            if calls < 3:
                raise PermissionError("temporarily locked")
            real_replace(src, dst)

        with (
            patch.object(utils.os, "replace", side_effect=flaky_replace),
            patch.object(utils, "_is_contended_windows_replace_error", return_value=True),
        ):
            assert atomic_replace(tmp_file, target) == str(target)

        assert calls == 3
        assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}

    def test_concurrent_writes_dont_corrupt(self, tmp_path):
        """Multiple rapid writes should each produce valid JSON."""
        import threading

        target = tmp_path / "concurrent.json"
        errors = []

        def writer(n):
            try:
                atomic_json_write(target, {"writer": n, "data": list(range(100))})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # File should contain valid JSON from one of the writers
        result = json.loads(target.read_text())
        assert "writer" in result
        assert len(result["data"]) == 100
