from __future__ import annotations

import asyncio

import pytest
from fastapi.routing import APIRoute

from hermes_cli import web_server


def test_security_routes_are_registered() -> None:
    routes = {
        (method, route.path)
        for route in web_server.app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }
    assert ("GET", "/api/security/status") in routes
    assert ("POST", "/api/security/scan") in routes
    assert ("POST", "/api/security/update") in routes
    assert ("DELETE", "/api/security/quarantine/{item_id}") in routes


def test_scan_with_quarantine_requires_explicit_confirmation() -> None:
    body = web_server.SecurityScanRequest(scope="quick", quarantine=True, confirmed=False)
    with pytest.raises(web_server.HTTPException) as caught:
        asyncio.run(web_server.security_scan(body))
    assert caught.value.status_code == 409


def test_feed_update_requires_explicit_confirmation() -> None:
    body = web_server.SecurityMutationRequest(confirmed=False)
    with pytest.raises(web_server.HTTPException) as caught:
        asyncio.run(web_server.security_update(body))
    assert caught.value.status_code == 409


def test_watch_mutation_requires_explicit_confirmation() -> None:
    body = web_server.SecurityWatchRequest(action="disable", confirmed=False)
    with pytest.raises(web_server.HTTPException) as caught:
        asyncio.run(web_server.security_watch(body))
    assert caught.value.status_code == 409
