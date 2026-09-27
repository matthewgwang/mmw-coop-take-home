import time
from collections import OrderedDict, deque
from collections.abc import Callable
from typing import Protocol


class RateLimiter(Protocol):
    """Anything with this method can stand in for a rate limiter."""

    def allow(self, client_id: str) -> bool: ...


class SlidingWindowLimiter:
    """At most `limit` accepted requests per client in any rolling `window` seconds.

    A request made exactly `window` seconds ago is outside the window. Denied
    requests are not recorded. Not thread-safe.

    Idle clients are evicted inside allow(). Clients are kept in order of their
    most recent accepted request, so the idle ones are always at the front and
    each call only looks at the clients it removes, plus one. That makes
    eviction amortized O(1) per call, even with millions of clients.
    """

    def __init__(
        self,
        limit: int,
        window: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if window <= 0:
            raise ValueError("window must be positive")
        self._limit = limit
        self._window = window
        self._clock = clock
        # client_id -> timestamps of accepted requests, oldest first. Every log in
        # here is non-empty, and clients are ordered by their newest timestamp.
        self._clients: OrderedDict[str, deque[float]] = OrderedDict()

    def allow(self, client_id: str) -> bool:
        now = self._clock()
        self._evict_idle_clients(now)

        log = self._clients.get(client_id)
        if log is None:
            log = deque()
        else:
            while now - log[0] >= self._window:
                log.popleft()

        if len(log) >= self._limit:
            return False

        log.append(now)
        self._clients[client_id] = log
        self._clients.move_to_end(client_id)
        return True

    def _evict_idle_clients(self, now: float) -> None:
        """Drop clients whose newest accepted request has left the window."""
        while self._clients:
            client_id, log = next(iter(self._clients.items()))
            if now - log[-1] < self._window:
                return
            del self._clients[client_id]