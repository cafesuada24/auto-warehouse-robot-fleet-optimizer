import contextlib
import contextvars
from collections.abc import Iterator, Mapping
from types import MappingProxyType
from typing import Final

# Per-task/per-request context. Each async task gets its own value.
_LOG_CONTEXT: Final[contextvars.ContextVar[MappingProxyType[str, object]]] = (
    contextvars.ContextVar(
        'log_context',
        default=MappingProxyType({}),
    )
)

_RESERVED_KEYS: Final[frozenset[str]] = frozenset(
    {
        # Avoid collisions with your static fields and common record keys.
        'service',
        'version',
        'ts',
        'level',
        'logger',
        'msg',
        'exc_info',
    },
)


def get_context() -> dict[str, object]:
    """Get the current context for the current task."""
    return dict(_LOG_CONTEXT.get())


def clear_context() -> None:
    """Clear the context var for the current task."""
    _LOG_CONTEXT.set(MappingProxyType({}))


def bind_context(
    fields: Mapping[str, object],
    *,
    allow_reserved: bool = False,
) -> None:
    if not allow_reserved:
        bad = _RESERVED_KEYS.intersection(fields.keys())
        if bad:
            raise KeyError(f'Reserved log context keys not allowed: {sorted(bad)}')

    current = _LOG_CONTEXT.get()
    merged = {**current, **dict(fields)}
    _LOG_CONTEXT.set(MappingProxyType(merged))


@contextlib.contextmanager
def context_scope(
    fields: Mapping[str, object],
    *,
    allow_reserved: bool = False,
) -> Iterator[None]:
    """Temporarily bind context fields for a block, then restore previous state.

    Works for sync code. For async, it still works within the same task.
    """
    if not allow_reserved:
        bad = _RESERVED_KEYS.intersection(fields.keys())
        if bad:
            raise KeyError(f'Reserved log context keys not allowed: {sorted(fields)}')

    token = _LOG_CONTEXT.set(MappingProxyType({**_LOG_CONTEXT.get(), **dict(fields)}))
    try:
        yield
    finally:
        _LOG_CONTEXT.reset(token)
