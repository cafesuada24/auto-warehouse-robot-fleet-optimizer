import threading
from concurrent.futures import ThreadPoolExecutor

from awrfo.singleton import SingletonMeta, ThreadSafeSingletonMeta

# ---------- Test Classes ----------

class NonThreadSafeService(metaclass=SingletonMeta):
    pass


class ThreadSafeService(metaclass=ThreadSafeSingletonMeta):
    pass

def create_instance(cls: type) -> int:
    """
    Returns the id() of the created instance.
    Using id() is crucial to detect multiple instantiations.
    """
    return id(cls())


def run_concurrently(cls: type, workers: int = 50) -> set[int]:
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return set(executor.map(create_instance, [cls] * workers))


# ---------- Tests ----------

def test_non_thread_safe_singleton_single_thread() -> None:
    a = NonThreadSafeService()
    b = NonThreadSafeService()
    assert a is b


def test_thread_safe_singleton_single_thread() -> None:
    a = ThreadSafeService()
    b = ThreadSafeService()
    assert a is b


def test_thread_safe_singleton_multi_thread() -> None:
    """
    Thread-safe singleton MUST return exactly one instance
    under concurrent access.
    """
    instance_ids = run_concurrently(ThreadSafeService, workers=100)
    assert len(instance_ids) == 1


def test_non_thread_safe_singleton_multi_thread() -> None:
    """
    Non-thread-safe singleton MAY create multiple instances
    under concurrent access.

    This test intentionally asserts that a race condition
    is observable.
    """
    barrier = threading.Barrier(30)

    class S(metaclass=SingletonMeta):
        def __init__(self) -> None:
            # Force many threads to be "inside creation" together
            barrier.wait()

    def make() -> int:
        return id(S())

    with ThreadPoolExecutor(max_workers=30) as ex:
        ids = set(ex.map(lambda _: make(), range(30)))

    # Now this becomes *much* more likely to show duplicates.
    # Still theoretically not 100% guaranteed, but close in practice.
    assert len(ids) > 1


def test_thread_safe_singleton_is_stable_across_calls() -> None:
    first = ThreadSafeService()
    for _ in range(100):
        assert ThreadSafeService() is first
