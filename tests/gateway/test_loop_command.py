"""Gateway /loop command tests — dispatch, routing capture, mid-run guard."""

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.platforms.base import MessageEvent, MessageType
from gateway.run import GatewayRunner
from gateway.session import SessionSource, SessionStore
from hermes_cli import loops


class _FakeSessionEntry:
    session_id = "sid-gateway-loop"


class _FakeSessionStore:
    def __init__(self):
        self.entry = _FakeSessionEntry()

    def get_or_create_session(self, source):
        return self.entry

    def _generate_session_key(self, source):
        return "agent:main:discord:channel:loop-test"


@pytest.fixture
def loop_env(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    loops._DB_CACHE.clear()
    yield home
    loops._DB_CACHE.clear()


def _make_runner():
    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(
        platforms={Platform.DISCORD: PlatformConfig(enabled=True, token="token")}
    )
    runner.session_store = _FakeSessionStore()
    runner.adapters = {}
    runner._queued_events = {}
    return runner


def _make_event(text: str) -> MessageEvent:
    return MessageEvent(
        text=text,
        message_type=MessageType.TEXT,
        source=SessionSource(
            platform=Platform.DISCORD,
            chat_id="chat-loop",
            chat_type="channel",
            thread_id="thread-9",
            user_id="user-loop",
        ),
        message_id="msg-loop",
    )


@pytest.mark.asyncio
async def test_gateway_loop_create_captures_route(loop_env):
    runner = _make_runner()
    response = await GatewayRunner._handle_loop_command(runner, _make_event("/loop 5m check the deploy"))
    assert "Loop set" in response
    assert "every 5m" in response

    state = loops.load_loop("sid-gateway-loop")
    assert state is not None
    assert state.prompt == "check the deploy"
    assert state.route["platform"] == "discord"
    assert state.route["chat_id"] == "chat-loop"
    assert state.route["thread_id"] == "thread-9"


@pytest.mark.asyncio
async def test_gateway_loop_status_pause_stop(loop_env):
    runner = _make_runner()
    await GatewayRunner._handle_loop_command(runner, _make_event("/loop 5m poll CI"))

    status = await GatewayRunner._handle_loop_command(runner, _make_event("/loop status"))
    assert "poll CI" in status

    paused = await GatewayRunner._handle_loop_command(runner, _make_event("/loop pause"))
    assert "paused" in paused.lower()

    stopped = await GatewayRunner._handle_loop_command(runner, _make_event("/loop stop"))
    assert "stopped" in stopped.lower()


@pytest.mark.asyncio
async def test_gateway_loop_goal_note_when_goal_active(loop_env):
    from hermes_cli.goals import GoalManager

    GoalManager(session_id="sid-gateway-loop").set("finish the migration")
    runner = _make_runner()
    response = await GatewayRunner._handle_loop_command(runner, _make_event("/loop 5m poll CI"))
    assert "active /goal" in response


@pytest.mark.asyncio
async def test_post_turn_loop_completion_completes_inflight_tick(loop_env):
    runner = _make_runner()
    await GatewayRunner._handle_loop_command(runner, _make_event("/loop 5m poll CI"))

    mgr = loops.LoopManager(session_id="sid-gateway-loop")
    mgr.state.next_due_at = time.time() - 1
    assert mgr.fire_tick() is not None

    entry = _FakeSessionEntry()
    await GatewayRunner._post_turn_loop_completion(
        runner,
        session_entry=entry,
        source=None,
        final_response="CI is done.\nLOOP_COMPLETE",
    )
    reloaded = loops.load_loop("sid-gateway-loop")
    assert reloaded.status == "done"


@pytest.mark.asyncio
async def test_post_turn_loop_completion_noop_without_inflight_tick(loop_env):
    runner = _make_runner()
    await GatewayRunner._handle_loop_command(runner, _make_event("/loop 5m poll CI"))
    entry = _FakeSessionEntry()
    # No tick fired — the ordinary user turn must not consume loop state.
    await GatewayRunner._post_turn_loop_completion(
        runner,
        session_entry=entry,
        source=None,
        final_response="regular reply LOOP_COMPLETE",
    )
    reloaded = loops.load_loop("sid-gateway-loop")
    assert reloaded.status == "active"
    assert reloaded.ticks_fired == 0


def test_session_reset_clears_only_the_outgoing_loop(loop_env):
    """/new retires its old loop; compression has a dedicated migration path."""
    store = SessionStore(sessions_dir=loop_env / "sessions", config=GatewayConfig())
    source = _make_event("hello").source
    old_entry = store.get_or_create_session(source)
    Loop = loops.LoopManager
    Loop(session_id=old_entry.session_id).set("watch deploy", interval_seconds=60)

    new_entry = store.reset_session(old_entry.session_key)

    assert new_entry is not None
    assert new_entry.session_id != old_entry.session_id
    old_loop = loops.load_loop(old_entry.session_id)
    assert old_loop is not None and old_loop.status == "cleared"
    assert loops.load_loop(new_entry.session_id) is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current_session_id", "authorized", "should_dispatch"),
    [
        ("sid-current", True, False),
        ("sid-loop", False, False),
        ("sid-loop", True, True),
    ],
)
async def test_loop_watcher_fences_session_and_sender_before_injection(
    loop_env,
    monkeypatch,
    current_session_id,
    authorized,
    should_dispatch,
):
    """Due loops must be scoped to the still-current, authorized source."""
    runner = object.__new__(GatewayRunner)
    source = _make_event("loop").source
    session_key = "agent:main:discord:channel:loop-test"
    state = loops.LoopManager(session_id="sid-loop").set(
        "poll CI",
        interval_seconds=60,
        route={
            "platform": Platform.DISCORD.value,
            "chat_id": str(source.chat_id),
            "chat_type": str(source.chat_type),
            "thread_id": str(source.thread_id),
            "user_id": str(source.user_id),
        },
    )
    state.next_due_at = time.time() - 1
    loops.save_loop("sid-loop", state)

    received = []

    async def handle_message(event):
        received.append(event)
        runner._running = False

    adapter = SimpleNamespace(handle_message=AsyncMock(side_effect=handle_message))
    runner._running = True
    runner.adapters = {Platform.DISCORD: adapter}
    runner._running_agents = {}
    runner.session_store = SimpleNamespace()
    runner._async_session_store = SimpleNamespace(
        _store=runner.session_store,
        lookup_by_session_key=AsyncMock(
            return_value=SimpleNamespace(session_id=current_session_id)
        ),
    )
    runner._build_process_event_source = lambda _evt: source
    runner._session_key_for_source = lambda _source: session_key
    runner._is_user_authorized = MagicMock(return_value=authorized)

    sleeps = 0

    async def no_wait(_delay):
        nonlocal sleeps
        sleeps += 1
        # Initial five-second startup delay is call one; stop after the first
        # scan if the stale/revoked path did not already stop via delivery.
        if sleeps > 1:
            runner._running = False

    monkeypatch.setattr("gateway.run.asyncio.sleep", no_wait)
    await runner._loop_wakeup_watcher(interval=0)

    if should_dispatch:
        adapter.handle_message.assert_awaited_once()
        event = received[0]
        assert event.metadata == {
            "gateway_session_key": session_key,
            "gateway_session_id": "sid-loop",
            "gateway_session_strict": True,
            "gateway_loop_session_id": "sid-loop",
        }
        assert loops.load_loop("sid-loop").status == "active"
    else:
        adapter.handle_message.assert_not_awaited()
        assert loops.load_loop("sid-loop").status == "cleared"
