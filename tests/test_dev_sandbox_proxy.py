"""Regression tests for the dev sandbox's outbound HTTPS boundary."""

from __future__ import annotations

import importlib.util
import ssl
import sys
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROXY_PATH = ROOT / "scripts" / "sandbox" / "proxy.py"


def _load_proxy(tmp_path: Path):
    spec = importlib.util.spec_from_file_location("dev_sandbox_proxy", PROXY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    argv = ["proxy.py", str(tmp_path), str(tmp_path), str(tmp_path / "ca.pem")]
    with patch.object(sys, "argv", argv):
        spec.loader.exec_module(module)
    return module


def test_https_handshake_eof_retries_before_any_request(tmp_path: Path) -> None:
    proxy = _load_proxy(tmp_path)
    raw_connections = [Mock(), Mock(), Mock()]
    upstream = Mock()
    context = Mock()
    context.wrap_socket.side_effect = [
        ssl.SSLEOFError(8, "unexpected EOF"),
        ssl.SSLEOFError(8, "unexpected EOF"),
        upstream,
    ]

    with (
        patch.object(proxy.socket, "create_connection", side_effect=raw_connections),
        patch.object(proxy.time, "sleep") as sleep,
    ):
        result = proxy.open_https_upstream(context, "registry.npmjs.org", 443)

    assert result is upstream
    assert raw_connections[0].close.call_count == 1
    assert raw_connections[1].close.call_count == 1
    assert raw_connections[2].close.call_count == 0
    assert sleep.call_args_list == [call(0.25), call(0.5)]


def test_https_certificate_failure_is_not_retried(tmp_path: Path) -> None:
    proxy = _load_proxy(tmp_path)
    raw = Mock()
    context = Mock()
    context.wrap_socket.side_effect = ssl.SSLCertVerificationError(
        1, "certificate verify failed"
    )

    with (
        patch.object(proxy.socket, "create_connection", return_value=raw) as connect,
        patch.object(proxy.time, "sleep") as sleep,
    ):
        with pytest.raises(ssl.SSLCertVerificationError):
            proxy.open_https_upstream(context, "registry.npmjs.org", 443)

    assert connect.call_count == 1
    assert raw.close.call_count == 1
    sleep.assert_not_called()
