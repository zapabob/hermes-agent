from __future__ import annotations

import errno
from collections.abc import Callable

import pytest

from downstream.platform.windows.filesystem import (
    DEFAULT_REPLACE_DELAYS,
    replace_with_retry,
)


def windows_error(code: int) -> OSError:
    error = OSError(f"synthetic Windows error {code}")
    setattr(error, "winerror", code)
    return error


def test_default_retry_delays_are_preserved() -> None:
    assert DEFAULT_REPLACE_DELAYS == (0.025, 0.05, 0.1, 0.2)


@pytest.mark.parametrize(
    ("error_factory", "retryable"),
    [
        pytest.param(lambda: PermissionError("denied"), True, id="permission"),
        pytest.param(lambda: windows_error(5), True, id="winerror-5"),
        pytest.param(lambda: windows_error(32), True, id="winerror-32"),
        pytest.param(lambda: windows_error(33), True, id="winerror-33"),
        pytest.param(lambda: FileNotFoundError("missing"), False, id="missing"),
        pytest.param(
            lambda: OSError(errno.EXDEV, "cross-device"), False, id="exdev"
        ),
        pytest.param(lambda: RuntimeError("unexpected"), False, id="non-oserror"),
    ],
)
def test_retry_trace_and_original_exception_are_preserved(
    error_factory: Callable[[], Exception], retryable: bool
) -> None:
    failure = error_factory()
    calls: list[tuple[str, str]] = []
    sleeps: list[float] = []

    def failing_replace(source: str, destination: str) -> None:
        calls.append((source, destination))
        raise failure

    with pytest.raises(type(failure)) as captured:
        replace_with_retry(
            "staged", "live", replace=failing_replace, sleep=sleeps.append
        )

    expected_attempts = len(DEFAULT_REPLACE_DELAYS) + 1 if retryable else 1
    assert calls == [("staged", "live")] * expected_attempts
    assert sleeps == (list(DEFAULT_REPLACE_DELAYS) if retryable else [])
    assert captured.value is failure


@pytest.mark.parametrize("failures_before_success", [0, 1, 2, 3, 4])
def test_success_on_each_allowed_attempt_preserves_trace(
    failures_before_success: int,
) -> None:
    calls: list[tuple[str, str]] = []
    sleeps: list[float] = []

    def eventually_replace(source: str, destination: str) -> None:
        calls.append((source, destination))
        if len(calls) <= failures_before_success:
            raise PermissionError("synthetic lock")

    result = replace_with_retry(
        "staged", "live", replace=eventually_replace, sleep=sleeps.append
    )

    assert result is None
    assert len(calls) == failures_before_success + 1
    assert sleeps == list(DEFAULT_REPLACE_DELAYS[:failures_before_success])


def test_empty_retry_schedule_makes_exactly_one_attempt() -> None:
    calls: list[tuple[str, str]] = []
    sleeps: list[float] = []

    def fail(source: str, destination: str) -> None:
        calls.append((source, destination))
        raise PermissionError("synthetic lock")

    with pytest.raises(PermissionError, match="synthetic lock"):
        replace_with_retry(
            "staged", "live", delays=(), replace=fail, sleep=sleeps.append
        )

    assert calls == [("staged", "live")]
    assert sleeps == []


def test_sensitivity_extra_sleep_is_detected_as_contract_break() -> None:
    """Comparator sensitivity: one mutated delay must fail the preserved schedule."""
    sleeps: list[float] = []

    def fail(_source: str, _destination: str) -> None:
        raise PermissionError("locked")

    with pytest.raises(PermissionError):
        replace_with_retry(
            "staged",
            "live",
            delays=(0.025, 0.05),
            replace=fail,
            sleep=sleeps.append,
        )

    mutated = list(sleeps)
    mutated[0] = 0.026
    assert mutated != list(DEFAULT_REPLACE_DELAYS[:2])
    assert sleeps == [0.025, 0.05]
