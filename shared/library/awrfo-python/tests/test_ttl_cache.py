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

    assert cache.try_add('a', ts_ms=1_000) is True
    assert cache.try_add('a', ts_ms=1_050) is False  # within TTL


def test_try_add_after_expiration_returns_true_again() -> None:
    cache = TTLCache[str](expire_period_ms=100, use_wall_timer=False)

    assert cache.try_add('a', ts_ms=1_000) is True
    assert cache.try_add('a', ts_ms=1_050) is False  # still live

    # Expired at 1_100. At ts_ms >= 1_100 it should be evicted and re-add should succeed.
    assert cache.try_add('a', ts_ms=1_100) is True


def test_evicts_oldest_entries_in_order_so_set_does_not_block_readd() -> None:
    cache = TTLCache[int](expire_period_ms=10, use_wall_timer=False)

    assert cache.try_add(1, ts_ms=100) is True  # expires at 110
    assert cache.try_add(2, ts_ms=101) is True  # expires at 111

    # At ts=110: entry 1 expired, entry 2 not yet.
    assert cache.try_add(1, ts_ms=110) is True  # should succeed (1 evicted)
    assert cache.try_add(2, ts_ms=110) is False  # should still be present


def test_use_wall_timer_false_requires_timestamp() -> None:
    cache = TTLCache[int](use_wall_timer=False)

    with pytest.raises(ValueError, match='timestamp must be provided'):
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


def test_remove_absent_value_is_noop() -> None:
    cache = TTLCache[int](expire_period_ms=100, use_wall_timer=False)

    # Should not raise
    cache.remove(123, ts_ms=1_000)
    cache.remove(123)  # also fine


def test_remove_present_value_allows_readd() -> None:
    cache = TTLCache[str](expire_period_ms=100, use_wall_timer=False)

    assert cache.try_add('a', ts_ms=1_000) is True
    assert cache.try_add('a', ts_ms=1_001) is False  # present

    cache.remove('a')  # removes from set

    # Since membership is checked via set, re-add should succeed immediately.
    assert cache.try_add('a', ts_ms=1_002) is True


def test_remove_only_affects_target_value() -> None:
    cache = TTLCache[int](expire_period_ms=100, use_wall_timer=False)

    assert cache.try_add(1, ts_ms=1_000) is True
    assert cache.try_add(2, ts_ms=1_000) is True

    cache.remove(1)

    assert cache.try_add(1, ts_ms=1_001) is True  # removed => can re-add
    assert cache.try_add(2, ts_ms=1_001) is False  # still present


def test_remove_with_ts_ms_triggers_eviction_of_expired_entries() -> None:
    cache = TTLCache[int](expire_period_ms=100, use_wall_timer=False)

    # Add two values at different timestamps
    assert cache.try_add(1, ts_ms=1_000) is True  # expires at 1_100
    assert cache.try_add(2, ts_ms=1_050) is True  # expires at 1_150

    # Move time to 1_100: value 1 should be expired; value 2 should still be live.
    # Call remove on an existing value to ensure the code path reaches __evict(ts_ms).
    cache.remove(2, ts_ms=1_100)

    # If eviction happened, 1 should be gone and re-add should succeed.
    assert cache.try_add(1, ts_ms=1_100) is True

    # 2 was explicitly removed, so it should be addable too.
    assert cache.try_add(2, ts_ms=1_101) is True


def test_remove_thread_safety_multiple_removers_and_adders() -> None:
    cache = TTLCache[int](expire_period_ms=10_000, use_wall_timer=False)
    assert cache.try_add(7, ts_ms=1_000) is True

    barrier = threading.Barrier(20)
    add_results: list[bool] = []
    add_lock = threading.Lock()

    def remover() -> None:
        barrier.wait()
        cache.remove(7)

    def adder() -> None:
        barrier.wait()
        ok = cache.try_add(7, ts_ms=1_001)
        with add_lock:
            add_results.append(ok)

    # Mix removers and adders
    threads: list[threading.Thread] = []
    for _ in range(10):
        threads.append(threading.Thread(target=remover))
    for _ in range(10):
        threads.append(threading.Thread(target=adder))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # At least one adder should succeed eventually because removers clear membership.
    assert any(add_results)
