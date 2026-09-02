"""Regression tests for the dev sandbox's outbound HTTPS boundary."""

from __future__ import annotations

import importlib.util
import ssl
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
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


def test_close_request_replaces_keep_alive_headers(tmp_path: Path) -> None:
    proxy = _load_proxy(tmp_path)
    request = (
        b"GET /package HTTP/1.1\r\n"
        b"Host: registry.npmjs.org\r\n"
        b"Connection: keep-alive\r\n"
        b"Proxy-Connection: keep-alive\r\n"
        b"X-Request: preserved\r\n\r\nbody"
    )

    closed = proxy.close_request(request)

    assert b"Connection: keep-alive" not in closed
    assert b"Proxy-Connection: keep-alive" not in closed
    assert closed.count(b"Connection: close") == 1
    assert b"X-Request: preserved\r\n" in closed
    assert closed.endswith(b"\r\n\r\nbody")


def test_only_fixture_hosts_require_tls_interception(tmp_path: Path) -> None:
    proxy = _load_proxy(tmp_path)
    (tmp_path / "hermes-agent.nousresearch.com").mkdir()

    assert proxy.has_fixture_host("hermes-agent.nousresearch.com")
    assert not proxy.has_fixture_host("registry.npmjs.org")
    assert not proxy.has_fixture_host("../registry.npmjs.org")


def test_non_fixture_connect_uses_opaque_tunnel(tmp_path: Path) -> None:
    proxy = _load_proxy(tmp_path)
    client = Mock()
    upstream = Mock()
    upstream_context = Mock()
    upstream_context.__enter__ = Mock(return_value=upstream)
    upstream_context.__exit__ = Mock(return_value=False)

    with (
        patch.object(
            proxy.socket, "create_connection", return_value=upstream_context
        ) as connect,
        patch.object(proxy, "relay_tunnel") as relay_tunnel,
    ):
        proxy.handle_connect(client, "registry.npmjs.org:443")

    connect.assert_called_once_with(
        ("registry.npmjs.org", 443), timeout=proxy.UPSTREAM_TIMEOUT_SECONDS
    )
    client.sendall.assert_called_once_with(
        b"HTTP/1.1 200 Connection Established\r\n\r\n"
    )
    relay_tunnel.assert_called_once_with(client, upstream)


def test_https_handshake_eof_exhausts_bounded_backoff(tmp_path: Path) -> None:
    proxy = _load_proxy(tmp_path)
    raw_connections = [Mock() for _ in range(proxy.UPSTREAM_TLS_HANDSHAKE_ATTEMPTS)]
    context = Mock()
    context.wrap_socket.side_effect = [
        ssl.SSLEOFError(8, "unexpected EOF") for _ in raw_connections
    ]

    with (
        patch.object(proxy.socket, "create_connection", side_effect=raw_connections),
        patch.object(proxy.time, "sleep") as sleep,
    ):
        with pytest.raises(ssl.SSLEOFError):
            proxy.open_https_upstream(context, "registry.npmjs.org", 443)

    assert all(raw.close.call_count == 1 for raw in raw_connections)
    assert sleep.call_args_list == [
        call(0.25),
        call(0.5),
        call(1.0),
        call(2.0),
        call(2.0),
    ]


def test_https_handshakes_are_serialized(tmp_path: Path) -> None:
    proxy = _load_proxy(tmp_path)
    first_entered = threading.Event()
    release_first = threading.Event()
    second_invoked = threading.Event()
    second_entered = threading.Event()
    upstreams = [Mock(), Mock()]
    context = Mock()
    call_count = 0

    def wrap_socket(raw, *, server_hostname):
        nonlocal call_count
        assert server_hostname == "registry.npmjs.org"
        call_count += 1
        if call_count == 1:
            first_entered.set()
            assert release_first.wait(timeout=1)
        else:
            second_entered.set()
        return upstreams[call_count - 1]

    def open_second():
        second_invoked.set()
        return proxy.open_https_upstream(context, "registry.npmjs.org", 443)

    context.wrap_socket.side_effect = wrap_socket
    with (
        patch.object(
            proxy.socket, "create_connection", side_effect=[Mock(), Mock()]
        ) as connect,
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        first = pool.submit(
            proxy.open_https_upstream, context, "registry.npmjs.org", 443
        )
        assert first_entered.wait(timeout=1)
        second = pool.submit(open_second)
        assert second_invoked.wait(timeout=1)
        assert not second_entered.wait(timeout=0.1)
        release_first.set()

        assert first.result(timeout=1) is upstreams[0]
        assert second.result(timeout=1) is upstreams[1]

    assert connect.call_count == 2
