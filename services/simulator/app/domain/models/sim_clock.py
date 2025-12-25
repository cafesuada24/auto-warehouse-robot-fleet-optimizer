import threading
from time import monotonic

from pydantic import NonNegativeInt
from pydantic.dataclasses import dataclass


@dataclass
class SimClock:
    """Deterministic simulation clock advanced by discrete ticks.

    - time_ms is advanced only by tick() in the simulation thread.
    - Any thread may read time_ms/time_s safely.
    """

    tick_ms: NonNegativeInt

    def __post_init__(self) -> None:
        self.__lock = threading.Lock()
        self.__cv = threading.Condition(self.__lock)

        self.__time_ms: NonNegativeInt = 0
        self.__tick_count: NonNegativeInt = 0
        self.__running: bool = False

    def start(self, *, reset: bool = True) -> None:
        with self.__lock:
            self.__running = True
            if reset:
                self.__time_ms = 0
                self.__tick_count = 0
            self.__cv.notify_all()

    def stop(self) -> None:
        with self.__lock:
            self.__running = False
            self.__cv.notify_all()

    def tick(self) -> None:
        """Advance time by exactly one tick. Call only from the simulation thread."""
        with self.__lock:
            if not self.__running:
                return
            self.__tick_count += 1
            self.__time_ms += self.tick_ms
            self.__cv.notify_all()

    def time_ms(self) -> NonNegativeInt:
        with self.__lock:
            return self.__time_ms

    def time_s(self) -> float:
        with self.__lock:
            return self.__time_ms / 1000.0

    def tick_count(self) -> int:
        with self.__lock:
            return self.__tick_count

    def wait_for_tick(self, target_tick: int, timeout_s: float | None = None) -> bool:
        """Useful in tests: wait until tick_count >= target_tick.

        Returns True if reached, False on timeout.
        """
        end = None if timeout_s is None else (monotonic() + timeout_s)
        with self.__lock:
            while self.__tick_count < target_tick and self.__running:
                if end is None:
                    self.__cv.wait()
                else:
                    remaining = end - monotonic()
                    if remaining <= 0:
                        return False
                    self.__cv.wait(timeout=remaining)
            return self.__tick_count >= target_tick
