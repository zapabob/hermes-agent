"""Behavior checks for the development sandbox's HTTPS proxy."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PROXY_PATH = ROOT / "scripts" / "sandbox" / "proxy.py"


@pytest.fixture
def proxy_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    fixture_root = tmp_path / "http"
    cert_root = tmp_path / "certs"
    fixture_root.mkdir()
    cert_root.mkdir()
    real_ca = cert_root / "real-ca.pem"
    real_ca.touch()
    monkeypatch.setattr(
        sys,
        "argv",
        [str(PROXY_PATH), str(fixture_root), str(cert_root), str(real_ca)],
    )
    spec = importlib.util.spec_from_file_location("sandbox_proxy_under_test", PROXY_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, fixture_root


def test_only_fixture_hosts_require_tls_interception(proxy_module) -> None:
    proxy, fixture_root = proxy_module
    (fixture_root / "hermes-agent.nousresearch.com").mkdir()

    assert proxy.has_fixture_host("hermes-agent.nousresearch.com")
    assert not proxy.has_fixture_host("registry.npmjs.org")
    assert not proxy.has_fixture_host("../registry.npmjs.org")


def test_non_fixture_connect_uses_opaque_tunnel(proxy_module, monkeypatch) -> None:
    proxy, _ = proxy_module
    client = object()
    upstream = object()
    events: list[object] = []

    class UpstreamContext:
        def __enter__(self):
            return upstream

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(
        proxy.socket,
        "create_connection",
        lambda address, timeout: events.append((address, timeout)) or UpstreamContext(),
    )
    monkeypatch.setattr(
        proxy,
        "relay_tunnel",
        lambda source, destination: events.append((source, destination)),
    )

    class Client:
        def sendall(self, payload: bytes) -> None:
            events.append(payload)

    client = Client()
    proxy.handle_connect(client, "registry.npmjs.org:443")

    assert events == [
        (("registry.npmjs.org", 443), proxy.UPSTREAM_TIMEOUT_SECONDS),
        b"HTTP/1.1 200 Connection Established\r\n\r\n",
        (client, upstream),
    ]
