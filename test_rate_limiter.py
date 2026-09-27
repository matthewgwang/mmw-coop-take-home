import gc
import inspect
import time
import weakref
from collections.abc import Callable

import pytest

from rate_limiter import RateLimiter, SlidingWindowLimiter

LIMIT = 5
WINDOW = 10.0


def make_clock(start: float = 0.0) -> tuple[Callable[[], float], Callable[[float], None]]:
    """A fake clock: returns (clock, set_time). Time only moves when set_time is called."""
    current = [start]

    def clock() -> float:
        return current[0]

    def set_time(t: float) -> None:
        current[0] = t

    return clock, set_time


def make_limiter(
    limit: int = LIMIT, window: float = WINDOW, start: float = 0.0
) -> tuple[SlidingWindowLimiter, Callable[[float], None]]:
    clock, set_time = make_clock(start)
    return SlidingWindowLimiter(limit, window, clock=clock), set_time


# --- Time injection -----------------------------------------------------------

def test_default_clock_is_time_monotonic() -> None:
    default = inspect.signature(SlidingWindowLimiter).parameters["clock"].default
    assert default is time.monotonic


def test_default_clock_works_without_injection() -> None:
    limiter = SlidingWindowLimiter(1, WINDOW)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False


def test_frozen_injected_clock_keeps_denying() -> None:
    limiter, _ = make_limiter(limit=1)
    assert limiter.allow("a") is True
    for _ in range(100):
        assert limiter.allow("a") is False  # no real time matters, only the fake clock


def test_advancing_injected_clock_restores_access_without_sleeping() -> None:
    limiter, set_time = make_limiter(limit=1)
    assert limiter.allow("a") is True
    set_time(WINDOW)
    assert limiter.allow("a") is True


def test_clock_is_consulted_once_per_call() -> None:
    calls: list[None] = []

    def counting_clock() -> float:
        calls.append(None)
        return 0.0

    limiter = SlidingWindowLimiter(LIMIT, WINDOW, clock=counting_clock)
    for _ in range(7):
        limiter.allow("a")
    assert len(calls) == 7


# --- The limit ----------------------------------------------------------------

def test_sixth_request_in_five_request_window_is_denied() -> None:
    limiter, set_time = make_limiter()
    for t in range(5):
        set_time(float(t))
        assert limiter.allow("a") is True
    set_time(4.5)
    assert limiter.allow("a") is False


def test_limit_is_per_client() -> None:
    limiter, _ = make_limiter()
    for _ in range(LIMIT):
        assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    assert limiter.allow("b") is True


def test_window_is_rolling_not_fixed() -> None:
    limiter, set_time = make_limiter(limit=2)
    set_time(0.0)
    assert limiter.allow("a") is True
    set_time(5.0)
    assert limiter.allow("a") is True
    set_time(9.0)
    assert limiter.allow("a") is False   # 0 and 5 still in window
    set_time(10.0)
    assert limiter.allow("a") is True    # 0 aged out; window now holds 5, 10
    set_time(14.0)
    assert limiter.allow("a") is False   # 5 and 10 still in window
    set_time(15.0)
    assert limiter.allow("a") is True    # 5 aged out


# --- Exactly-W-seconds boundaries (exactly W ago is OUTSIDE the window) -------

def test_request_just_under_w_seconds_later_is_denied() -> None:
    limiter, set_time = make_limiter(limit=1)
    assert limiter.allow("a") is True
    set_time(9.999)
    assert limiter.allow("a") is False


def test_request_exactly_w_seconds_later_is_allowed() -> None:
    limiter, set_time = make_limiter(limit=1)
    assert limiter.allow("a") is True
    set_time(WINDOW)
    assert limiter.allow("a") is True


def test_exact_boundary_with_nonzero_start_and_fractional_window() -> None:
    limiter, set_time = make_limiter(limit=1, window=2.5, start=100.5)
    assert limiter.allow("a") is True
    set_time(102.9)
    assert limiter.allow("a") is False
    set_time(103.0)
    assert limiter.allow("a") is True


# --- Denied requests do not count ---------------------------------------------

def test_denied_requests_do_not_extend_the_block() -> None:
    limiter, set_time = make_limiter(limit=1)
    assert limiter.allow("a") is True
    set_time(5.0)
    assert limiter.allow("a") is False  # if this counted, "a" would be blocked until 15
    set_time(10.0)
    assert limiter.allow("a") is True


def test_hammering_client_gets_through_once_window_clears() -> None:
    limiter, set_time = make_limiter()
    for _ in range(LIMIT):
        limiter.allow("a")
    for i in range(1000):
        set_time(i * 0.009)  # 1000 denied attempts spread over 0..9 seconds
        assert limiter.allow("a") is False
    set_time(WINDOW)
    assert limiter.allow("a") is True


# --- Eviction and memory reclamation ------------------------------------------
# These inspect the private _clients map: eviction is invisible through allow().

def test_idle_clients_are_evicted_on_next_allow() -> None:
    limiter, set_time = make_limiter()
    for i in range(10_000):
        limiter.allow(f"one-time-{i}")
    assert len(limiter._clients) == 10_000

    set_time(WINDOW)
    limiter.allow("newcomer")
    assert list(limiter._clients) == ["newcomer"]


def test_evicted_client_memory_is_actually_freed() -> None:
    limiter, set_time = make_limiter()
    limiter.allow("old")
    old_log_ref = weakref.ref(limiter._clients["old"])

    set_time(WINDOW)
    limiter.allow("new")
    gc.collect()  # not needed on CPython (refcounting), kept for other interpreters
    assert old_log_ref() is None


def test_eviction_is_lazy_and_happens_inside_allow() -> None:
    limiter, set_time = make_limiter()
    limiter.allow("a")
    set_time(WINDOW * 100)
    assert "a" in limiter._clients  # nothing runs until allow() is called
    limiter.allow("b")
    assert "a" not in limiter._clients


def test_clients_with_any_timestamp_in_window_are_kept() -> None:
    limiter, set_time = make_limiter()
    set_time(0.0)
    limiter.allow("a")
    set_time(8.0)
    limiter.allow("a")
    set_time(10.0)
    limiter.allow("b")
    assert "a" in limiter._clients  # its t=8 request is still in the window


def test_client_log_is_trimmed_to_in_window_timestamps() -> None:
    limiter, set_time = make_limiter()
    for t in (0.0, 1.0, 8.0):
        set_time(t)
        limiter.allow("a")
    set_time(10.5)
    limiter.allow("a")
    assert list(limiter._clients["a"]) == [1.0, 8.0, 10.5]


def test_denied_request_does_not_keep_client_alive() -> None:
    limiter, set_time = make_limiter(limit=1)
    limiter.allow("a")          # t=0, accepted
    set_time(5.0)
    limiter.allow("a")          # denied: adds nothing
    set_time(10.0)
    limiter.allow("b")
    assert "a" not in limiter._clients


def test_recently_active_client_is_not_stuck_behind_idle_one() -> None:
    # Guards the ordering invariant: a client that becomes active again must move
    # to the back, otherwise it blocks eviction of idle clients queued behind it.
    limiter, set_time = make_limiter()
    set_time(0.0)
    limiter.allow("a")
    set_time(1.0)
    limiter.allow("b")
    set_time(5.0)
    limiter.allow("a")          # a's newest request is now later than b's
    set_time(11.0)
    limiter.allow("c")
    assert list(limiter._clients) == ["a", "c"]  # b evicted, a kept


# --- Construction and typing --------------------------------------------------

@pytest.mark.parametrize(
    ("limit", "window"),
    [(0, WINDOW), (-1, WINDOW), (LIMIT, 0.0), (LIMIT, -1.0)],
)
def test_invalid_configuration_raises(limit: int, window: float) -> None:
    with pytest.raises(ValueError):
        SlidingWindowLimiter(limit, window)


def test_satisfies_rate_limiter_protocol() -> None:
    limiter: RateLimiter = SlidingWindowLimiter(LIMIT, WINDOW)  # checked by mypy
    assert limiter.allow("a") is True