import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class _CacheEntry[V]:
    expire_ts_ms: int
    value: V


class TTLCache[V]:
    def __init__(
        self,
        max_size: int = 10_000,
        expire_period_ms: int = 10 * 60 * 1000,
        *,
        use_wall_timer: bool = True,
    ) -> None:
        self.__use_wall_timer = use_wall_timer
        self.__max_size = max_size
        self.__expire_period_ms = expire_period_ms
        self.__set: set[V] = set()
        self.__q: deque[_CacheEntry[V]] = deque(maxlen=max_size)
        self.__lock = threading.Lock()

    def try_add(self, value: V, ts_ms: int | None = None) -> bool:
        if ts_ms is None:
            if not self.__use_wall_timer:
                raise ValueError('timestamp must be provided if use_wall_timer is set')
            ts_ms = datetime.now().microsecond

        with self.__lock:
            self.__evict(ts_ms, ensure_avail=True)

            if value in self.__set:
                return False

            expr = ts_ms + self.__expire_period_ms
            self.__set.add(value)
            self.__q.append(_CacheEntry(expire_ts_ms=expr, value=value))
            return True

    def __evict(self, ts_ms: int, *, ensure_avail: bool = False) -> None:
        while (self.__q and self.__q[0].expire_ts_ms <= ts_ms) or (
            ensure_avail and len(self.__q) == self.__q.maxlen
        ):
            val = self.__q.popleft()
            self.__set.discard(val.value)
