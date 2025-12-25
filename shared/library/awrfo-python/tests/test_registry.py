import threading
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor

import pytest
from awrfo.registry import Registry
from awrfo.singleton import SingletonMeta

# -------------------------
# Fixtures / utilities
# -------------------------


@pytest.fixture(autouse=True)
def reset_singleton_state() -> Generator[None]:
    """
    A singleton registry will retain state across tests unless reset.

    This fixture clears the metaclass instance cache before/after each test.
    Adapt if your singleton implementation stores instances elsewhere.
    """
    # Clear before
    if hasattr(SingletonMeta, '_instances'):
        SingletonMeta._instances.clear()  # type: ignore[attr-defined]
    yield
    # Clear after
    if hasattr(SingletonMeta, '_instances'):
        SingletonMeta._instances.clear()  # type: ignore[attr-defined]


def get_cmd(reg: Registry, group: str, name: str) -> Callable[..., object]:
    snap = reg.get_registry()
    return snap[group][name]


# -------------------------
# Core behavior tests
# -------------------------


def test_registry_is_singleton() -> None:
    r1 = Registry()
    r2 = Registry()
    assert r1 is r2


def test_register_creates_group_and_command() -> None:
    reg = Registry()

    calls: list[tuple[int, int]] = []

    @reg.register_command('math', 'add')
    def add(a: int, b: int) -> None:
        calls.append((a, b))

    snap = reg.get_registry()
    assert 'math' in snap
    assert 'add' in snap['math']
    assert callable(snap['math']['add'])

    # Validate calling the stored wrapper triggers original behavior
    snap['math']['add'](1, 2)
    assert calls == [(1, 2)]

    # The decorated function itself should also work
    add(3, 4)
    assert calls == [(1, 2), (3, 4)]


def test_register_same_name_overwrites_previous() -> None:
    reg = Registry()

    called: list[str] = []

    @reg.register_command('g', 'cmd')
    def first() -> None:
        called.append('first')

    @reg.register_command('g', 'cmd')
    def second() -> None:
        called.append('second')

    snap = reg.get_registry()
    snap['g']['cmd']()
    assert called == ['second']

    # Ensure the later one is now the stored callable
    assert snap['g']['cmd'].__name__ == 'second'
    assert first.__name__ == 'first'
    assert second.__name__ == 'second'


def test_register_different_groups_are_isolated() -> None:
    reg = Registry()

    called: list[str] = []

    @reg.register_command('groupA', 'cmd')
    def cmd_a() -> None:
        called.append('A')

    @reg.register_command('groupB', 'cmd')
    def cmd_b() -> None:
        called.append('B')

    snap = reg.get_registry()
    snap['groupA']['cmd']()
    snap['groupB']['cmd']()
    assert called == ['A', 'B']


def test_wraps_preserves_metadata() -> None:
    reg = Registry()

    @reg.register_command('meta', 'f')
    def f(x: int) -> None:
        """Docstring should be preserved."""
        return None

    stored = get_cmd(reg, 'meta', 'f')
    assert stored.__name__ == 'f'
    assert stored.__doc__ == 'Docstring should be preserved.'


def test_registry_snapshot_is_outer_copy() -> None:
    reg = Registry()

    @reg.register_command('g', 'x')
    def x() -> None:
        return None

    snap1 = reg.get_registry()
    assert 'g' in snap1

    # Mutating snapshot outer dict must not affect registry
    snap1.pop('g')
    snap2 = reg.get_registry()
    assert 'g' in snap2


def test_registry_snapshot_is_inner_copy() -> None:
    reg = Registry()

    @reg.register_command('g', 'x')
    def x() -> None:
        return None

    snap1 = reg.get_registry()
    assert 'x' in snap1['g']

    # Mutate the inner dict copy
    snap1['g'].pop('x')

    snap2 = reg.get_registry()
    assert 'x' in snap2['g']


def test_register_returns_callable_with_same_name() -> None:
    reg = Registry()

    @reg.register_command('g', 'cmd')
    def cmd() -> None:
        return None

    assert cmd.__name__ == 'cmd'


# -------------------------
# Error / edge cases
# -------------------------


def test_can_register_empty_group_and_name() -> None:
    reg = Registry()

    called = False

    @reg.register_command('', '')
    def cmd() -> None:
        nonlocal called
        called = True

    snap = reg.get_registry()
    assert '' in snap
    assert '' in snap['']
    snap['']['']()
    assert called is True


def test_register_supports_functions_with_args_and_kwargs() -> None:
    reg = Registry()

    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    @reg.register_command('g', 'cmd')
    def cmd(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    snap = reg.get_registry()
    snap['g']['cmd'](1, 2, a=3, b=4)
    assert calls == [((1, 2), {'a': 3, 'b': 4})]


# -------------------------
# Concurrency tests
# -------------------------


def test_concurrent_registration_same_key_last_write_wins() -> None:
    """
    If Registry is NOT thread-safe, this test still should not crash.
    It verifies at least that some command ends up registered.

    If you want strict behavior under concurrency, make Registry thread-safe.
    """
    reg = Registry()
    barrier = threading.Barrier(20)

    def register(i: int) -> None:
        barrier.wait()

        @reg.register_command('g', 'cmd')
        def cmd() -> None:
            # capture i in closure
            _ = i

    with ThreadPoolExecutor(max_workers=20) as ex:
        list(ex.map(register, range(20)))

    snap = reg.get_registry()
    assert 'g' in snap and 'cmd' in snap['g']
    assert callable(snap['g']['cmd'])


def test_concurrent_read_while_registering_does_not_raise() -> None:
    """
    Reads during writes can raise RuntimeError if dict is mutated during iteration.
    Our get_registry() should copy safely (outer + inner), minimizing issues.
    This test asserts no exceptions occur under concurrent access.
    """
    reg = Registry()
    stop = threading.Event()
    errors: list[BaseException] = []

    def writer() -> None:
        i = 0
        while i < 500:
            try:

                @reg.register_command('g', f'cmd{i}')
                def cmd() -> None:
                    return None

                i += 1
            except BaseException as e:  # noqa: BLE001 (test harness)
                errors.append(e)
                break
        stop.set()

    def reader() -> None:
        while not stop.is_set():
            try:
                _ = reg.get_registry()
            except BaseException as e:  # noqa: BLE001 (test harness)
                errors.append(e)
                break

    t1 = threading.Thread(target=writer)
    t2 = threading.Thread(target=reader)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert errors == []
