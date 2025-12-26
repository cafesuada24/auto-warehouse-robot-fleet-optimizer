# test_ttl_cache.py
# Pytest testcases for TTLCache (Python 3.12)
#
# Assumptions these tests enforce (intended TTL semantics):
# - try_add(value, ts_ms) returns True the first time within the TTL window.
# - Adding the same value again within TTL returns False.
# - After the TTL has elapsed (ts_ms >= original_ts + expire_period_ms), the value is evicted
#   and can be added again (returns True).
# - When use_wall_timer=False, ts_ms must be provided.
# - Basic thread-safety: concurrent adds of the same value should yield exactly one True.

import threading

import pytest

# Import your TTLCache from the module where you defined it.
# Example:
# from my_cache_module import TTLCache
from awrfo.ttl_cache import TTLCache  # <-- change this


def test_try_add_first_time_returns_true() -> None:
    cache = TTLCache[int](expire_period_ms=100, use_wall_timer=False)

    assert cache.try_add(1, ts_ms=1_000) is True


def test_try_add_duplicate_within_ttl_returns_false() -> None:
    cache = TTLCache[str](expire_period_ms=100, use_wall_timer=False)

    assert cache.try_add("a", ts_ms=1_000) is True
    assert cache.try_add("a", ts_ms=1_050) is False  # within TTL


def test_try_add_after_expiration_returns_true_again() -> None:
    cache = TTLCache[str](expire_period_ms=100, use_wall_timer=False)

    assert cache.try_add("a", ts_ms=1_000) is True
    assert cache.try_add("a", ts_ms=1_050) is False  # still live

    # Expired at 1_100. At ts_ms >= 1_100 it should be evicted and re-add should succeed.
    assert cache.try_add("a", ts_ms=1_100) is True


def test_evicts_oldest_entries_in_order_so_set_does_not_block_readd() -> None:
    cache = TTLCache[int](expire_period_ms=10, use_wall_timer=False)

    assert cache.try_add(1, ts_ms=100) is True  # expires at 110
    assert cache.try_add(2, ts_ms=101) is True  # expires at 111

    # At ts=110: entry 1 expired, entry 2 not yet.
    assert cache.try_add(1, ts_ms=110) is True   # should succeed (1 evicted)
    assert cache.try_add(2, ts_ms=110) is False  # should still be present


def test_max_size_caps_queue_and_allows_eviction_by_capacity() -> None:
    # deque(maxlen=max_size) will drop the oldest entry when appending past capacity.
    # The cache should remain consistent: dropped value should not stay in __set forever.
    cache = TTLCache[int](max_size=2, expire_period_ms=10_000, use_wall_timer=False)

    assert cache.try_add(1, ts_ms=0) is True
    assert cache.try_add(2, ts_ms=1) is True
    assert cache.try_add(3, ts_ms=2) is True  # pushes out 1 from deque

    # Since 1 should have been dropped from the structure due to capacity,
    # a re-add should succeed (i.e., 1 must not remain in the internal set).
    assert cache.try_add(1, ts_ms=3) is True


def test_use_wall_timer_false_requires_timestamp() -> None:
    cache = TTLCache[int](use_wall_timer=False)

    with pytest.raises(ValueError, match="timestamp must be provided"):
        cache.try_add(1)


def test_thread_safety_only_one_wins_for_same_value() -> None:
    cache = TTLCache[int](expire_period_ms=10_000, use_wall_timer=False)

    barrier = threading.Barrier(20)
    results: list[bool] = []
    results_lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        ok = cache.try_add(42, ts_ms=1_000)
        with results_lock:
            results.append(ok)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count(True) == 1
    assert results.count(False) == 19
