"""Tests for the Chronos cron-fire webhook (POST /api/cron/fire) — Phase 4E.2.

The webhook authenticates a NAS-minted JWT via the pluggable fire-verifier
(NOT API_SERVER_KEY), then runs the job via the resolved provider's fire_due in
the background, returning 202. These tests monkeypatch the verifier and
resolve_cron_scheduler — the verifier itself is tested with real crypto in
test_chronos_verify.py.
"""

import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import PlatformConfig
from gateway.platforms.api_server import APIServerAdapter, cors_middleware

_MOD = "gateway.platforms.api_server"
FIRE_AT = "2026-08-16T12:00:00+00:00"


def _bound_claims(job_id: str) -> dict[str, str]:
    return {
        "purpose": "cron_fire",
        "cron_job_id": job_id,
        "cron_fire_at": FIRE_AT,
    }


def _bound_verifier(**kwargs):
    """Test token carries its bound job id; ``good`` is the common fixture."""
    token = str(kwargs.get("token") or "")
    return _bound_claims("abc123" if token == "good" else token)


def _fire_payload(job_id: str) -> dict[str, str]:
    return {"job_id": job_id, "fire_at": FIRE_AT}


def _make_adapter() -> APIServerAdapter:
    return APIServerAdapter(PlatformConfig(enabled=True, extra={"key": "sk-secret"}))


def _create_app(adapter: APIServerAdapter) -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app["api_server_adapter"] = adapter
    app.router.add_post("/api/cron/fire", adapter._handle_cron_fire)
    return app


@pytest.fixture
def adapter():
    return _make_adapter()


class _SpyProvider:
    """Records durable admission and claimed dispatch calls."""

    def __init__(self):
        self.claimed = []
        self.fired = []

    def claim_fire(self, job_id, *, expected_fire_at=None):
        self.claimed.append(job_id)
        assert expected_fire_at == FIRE_AT
        return {"id": job_id, "execution_id": f"exec-{job_id}"}

    def fire_claimed(self, job, *, adapters=None, loop=None):
        self.fired.append(job["id"])
        return True


@pytest.mark.asyncio
async def test_valid_fire_reservation_blocks_drain_before_body_and_task(adapter, monkeypatch):
    runner = SimpleNamespace(_draining=False, _external_drain_active=False)
    body_started = asyncio.Event()
    release_body = asyncio.Event()
    fired = threading.Event()
    release_fire = threading.Event()

    class BlockingProvider:
        def claim_fire(self, job_id, *, expected_fire_at=None):
            assert expected_fire_at == FIRE_AT
            return {"id": job_id, "execution_id": "exec-1"}

        def fire_claimed(self, job, *, adapters=None, loop=None):
            fired.set()
            release_fire.wait(timeout=2)
            return True

    original_json = web.Request.json

    async def delayed_json(request):
        body_started.set()
        await release_body.wait()
        return await original_json(request)

    monkeypatch.setattr("cron.scheduler_provider.resolve_cron_scheduler", BlockingProvider)
    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: _bound_verifier,
    )
    app = _create_app(adapter)
    with patch("gateway.run._gateway_runner_ref", lambda: runner), patch.object(
        web.Request, "json", delayed_json
    ):
        async with TestClient(TestServer(app)) as cli:
            request_task = asyncio.create_task(
                cli.post(
                    "/api/cron/fire",
                    headers={"Authorization": "Bearer good"},
                    json=_fire_payload("abc123"),
                )
            )
            await body_started.wait()
            assert adapter.active_agent_work_count() == 1

            release_body.set()
            response = await request_task
            assert response.status == 202
            await asyncio.to_thread(fired.wait, 2)
            assert adapter.active_agent_work_count() == 1
            release_fire.set()
            for _ in range(50):
                if adapter.active_agent_work_count() == 0:
                    break
                await asyncio.sleep(0.01)

    assert adapter.active_agent_work_count() == 0


@pytest.mark.asyncio
async def test_admission_failure_is_retryable_and_never_dispatches(adapter, monkeypatch):
    class FailingProvider(_SpyProvider):
        def claim_fire(self, job_id, *, expected_fire_at=None):
            raise OSError("ledger unavailable")

    provider = FailingProvider()
    monkeypatch.setattr("cron.scheduler_provider.resolve_cron_scheduler", lambda: provider)
    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: _bound_verifier,
    )

    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as cli:
        response = await cli.post(
            "/api/cron/fire",
            headers={"Authorization": "Bearer good"},
            json=_fire_payload("abc123"),
        )

    assert response.status == 503
    assert provider.fired == []
    assert adapter.active_agent_work_count() == 0


@pytest.mark.asyncio
async def test_accepted_response_waits_for_durable_admission(adapter, monkeypatch):
    claim_started = threading.Event()
    release_claim = threading.Event()

    class BlockingAdmissionProvider(_SpyProvider):
        def claim_fire(self, job_id, *, expected_fire_at=None):
            claim_started.set()
            release_claim.wait(timeout=2)
            return super().claim_fire(job_id, expected_fire_at=expected_fire_at)

    provider = BlockingAdmissionProvider()
    monkeypatch.setattr("cron.scheduler_provider.resolve_cron_scheduler", lambda: provider)
    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: _bound_verifier,
    )

    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as cli:
        request_task = asyncio.create_task(
            cli.post(
                "/api/cron/fire",
                headers={"Authorization": "Bearer good"},
                json=_fire_payload("abc123"),
            )
        )
        assert await asyncio.to_thread(claim_started.wait, 2)
        await asyncio.sleep(0)
        assert not request_task.done()

        release_claim.set()
        response = await request_task
        # The 202 guarantees durable ADMISSION only — the fire itself runs as
        # tracked background work, so wait for it to actually land (fast
        # locally, but CI scheduling can lose this race).
        for _ in range(200):
            if provider.fired:
                break
            await asyncio.sleep(0.01)

    assert response.status == 202
    assert provider.claimed == ["abc123"]
    assert provider.fired == ["abc123"]


@pytest.mark.asyncio
async def test_missing_job_id_400(adapter, monkeypatch):
    """Valid token but no job_id → 400, no fire."""
    spy = _SpyProvider()
    monkeypatch.setattr("cron.scheduler_provider.resolve_cron_scheduler", lambda: spy)
    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: _bound_verifier,
    )

    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as cli:
        resp = await cli.post("/api/cron/fire",
                              headers={"Authorization": "Bearer good"},
                              json={})
        assert resp.status == 400
    assert spy.fired == []


@pytest.mark.asyncio
async def test_missing_fire_at_400(adapter, monkeypatch):
    spy = _SpyProvider()
    monkeypatch.setattr("cron.scheduler_provider.resolve_cron_scheduler", lambda: spy)
    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: _bound_verifier,
    )

    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as cli:
        response = await cli.post(
            "/api/cron/fire",
            headers={"Authorization": "Bearer good"},
            json={"job_id": "abc123"},
        )
        assert response.status == 400
    assert spy.claimed == []


@pytest.mark.asyncio
async def test_fire_does_not_require_api_server_key(adapter, monkeypatch):
    """The fire endpoint must NOT gate on API_SERVER_KEY — auth is the NAS-JWT.
    A request with NO API key header but a valid fire token still succeeds."""
    spy = _SpyProvider()
    monkeypatch.setattr("cron.scheduler_provider.resolve_cron_scheduler", lambda: spy)
    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: _bound_verifier,
    )

    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as cli:
        # Bearer is the FIRE token, not the API_SERVER_KEY "sk-secret".
        resp = await cli.post("/api/cron/fire",
                               headers={"Authorization": "Bearer j9"},
                               json=_fire_payload("j9"))
        assert resp.status == 202
    for _ in range(50):
        if spy.fired:
            break
        await asyncio.sleep(0.01)
    assert spy.fired == ["j9"]


@pytest.mark.asyncio
async def test_sync_verifier_runs_off_the_event_loop(adapter, monkeypatch):
    """The verifier resolves the signing key from a JWKS URL — a synchronous
    HTTP GET on a cache miss. It must run via asyncio.to_thread, NOT inline on
    the event loop, or a slow/rate-limited portal stalls every other adapter
    sharing the loop. Proof: the sync verifier executes on a worker thread, not
    the loop thread.
    """
    loop_thread_id = threading.get_ident()
    seen = {}

    def blocking_verifier(**kw):
        seen["thread_id"] = threading.get_ident()
        return _bound_verifier(**kw)

    spy = _SpyProvider()
    monkeypatch.setattr("cron.scheduler_provider.resolve_cron_scheduler", lambda: spy)
    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: blocking_verifier,
    )

    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as cli:
        resp = await cli.post("/api/cron/fire",
                               headers={"Authorization": "Bearer off-loop"},
                               json=_fire_payload("off-loop"))
        assert resp.status == 202

    # If the verifier had run inline on the loop, its thread id would equal the
    # loop thread's; to_thread puts it on a distinct worker thread.
    assert seen["thread_id"] != loop_thread_id


@pytest.mark.asyncio
async def test_crashing_verifier_fails_closed_401(adapter, monkeypatch):
    """A verifier that raises must be treated as a rejection (401), never admit
    the fire, and never surface as a 500 — this is the only inbound that can
    trigger remote job execution, so it fails closed.
    """
    spy = _SpyProvider()
    monkeypatch.setattr("cron.scheduler_provider.resolve_cron_scheduler", lambda: spy)

    def exploding_verifier(**kw):
        raise RuntimeError("JWKS endpoint unreachable")

    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: exploding_verifier,
    )

    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as cli:
        resp = await cli.post("/api/cron/fire",
                              headers={"Authorization": "Bearer boom"},
                              json={"job_id": "abc123"})
        assert resp.status == 401

    await asyncio.sleep(0.05)
    assert spy.fired == []


@pytest.mark.asyncio
async def test_async_verifier_is_awaited(adapter, monkeypatch):
    """A coroutine verifier (a future async escape-hatch) is awaited directly
    rather than dispatched to a thread — a valid async verify still fires.
    """
    spy = _SpyProvider()
    monkeypatch.setattr("cron.scheduler_provider.resolve_cron_scheduler", lambda: spy)

    async def async_verifier(**kw):
        return _bound_verifier(**kw)

    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: async_verifier,
    )

    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as cli:
        resp = await cli.post("/api/cron/fire",
                               headers={"Authorization": "Bearer async-ok"},
                               json=_fire_payload("async-ok"))
        assert resp.status == 202

    for _ in range(50):
        if spy.fired:
            break
        await asyncio.sleep(0.01)
    assert spy.fired == ["async-ok"]


@pytest.mark.asyncio
async def test_signed_job_or_time_substitution_is_rejected_before_claim(adapter, monkeypatch):
    spy = _SpyProvider()
    monkeypatch.setattr("cron.scheduler_provider.resolve_cron_scheduler", lambda: spy)
    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: (lambda **kw: _bound_claims("signed-job")),
    )

    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as cli:
        response = await cli.post(
            "/api/cron/fire",
            headers={"Authorization": "Bearer signed-job"},
            json=_fire_payload("other-job"),
        )
        assert response.status == 401

    assert spy.claimed == []
    assert spy.fired == []


@pytest.mark.asyncio
async def test_legacy_provider_cannot_discard_signed_fire_time(adapter, monkeypatch):
    """The public webhook fails closed instead of calling unbound fire_due."""
    fired = []

    class LegacyProvider:
        def fire_due(self, job_id, *, adapters=None, loop=None):
            fired.append(job_id)
            return True

    monkeypatch.setattr(
        "cron.scheduler_provider.resolve_cron_scheduler",
        lambda: LegacyProvider(),
    )
    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: _bound_verifier,
    )

    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as cli:
        response = await cli.post(
            "/api/cron/fire",
            headers={"Authorization": "Bearer legacy-job"},
            json=_fire_payload("legacy-job"),
        )
        assert response.status == 503

    assert fired == []


@pytest.mark.asyncio
async def test_fire_passes_live_adapters_to_provider(adapter, monkeypatch):
    """The fire webhook must hand the gateway's live adapters to fire_claimed —
    delivery parity with the built-in ticker (gateway/run.py passes
    runner.adapters). Without them, relay-fronted logical platforms (whose
    ONLY send path is the live relay adapter — no native credential exists on
    the box) and E2EE platforms fail every external-provider fire with
    "platform 'X' not configured/enabled" while the same job delivers fine
    under the in-process ticker."""
    seen = {}

    class _AdapterSpyProvider(_SpyProvider):
        def fire_claimed(self, job, *, adapters=None, loop=None):
            seen["job_id"] = job["id"]
            seen["adapters"] = adapters
            seen["loop"] = loop
            return True

    live_adapters = {"relay": object()}
    runner = SimpleNamespace(
        _draining=False,
        _external_drain_active=False,
        adapters=live_adapters,
    )

    monkeypatch.setattr(
        "cron.scheduler_provider.resolve_cron_scheduler",
        lambda: _AdapterSpyProvider(),
    )
    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: _bound_verifier,
    )

    with patch("gateway.run._gateway_runner_ref", lambda: runner):
        app = _create_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.post("/api/cron/fire",
                                   headers={"Authorization": "Bearer with-adapters"},
                                   json=_fire_payload("with-adapters"))
            assert resp.status == 202

        for _ in range(50):
            if seen:
                break
            await asyncio.sleep(0.01)

    assert seen.get("job_id") == "with-adapters"
    assert seen.get("adapters") is live_adapters
    assert seen.get("loop") is not None


@pytest.mark.asyncio
async def test_fire_without_runner_passes_none_adapters(adapter, monkeypatch):
    """No gateway runner (standalone/edge case) → fire still works with
    adapters=None, preserving the historical standalone delivery path."""
    seen = {}

    class _AdapterSpyProvider(_SpyProvider):
        def fire_claimed(self, job, *, adapters=None, loop=None):
            seen["job_id"] = job["id"]
            seen["adapters"] = adapters
            return True

    monkeypatch.setattr(
        "cron.scheduler_provider.resolve_cron_scheduler",
        lambda: _AdapterSpyProvider(),
    )
    monkeypatch.setattr(
        "plugins.cron_providers.chronos.verify.get_fire_verifier",
        lambda: _bound_verifier,
    )

    with patch("gateway.run._gateway_runner_ref", lambda: None):
        app = _create_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.post("/api/cron/fire",
                                   headers={"Authorization": "Bearer no-runner"},
                                   json=_fire_payload("no-runner"))
            assert resp.status == 202

        for _ in range(50):
            if seen:
                break
            await asyncio.sleep(0.01)

    assert seen.get("job_id") == "no-runner"
    assert seen.get("adapters") is None
