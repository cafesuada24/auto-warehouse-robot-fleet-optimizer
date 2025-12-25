# Pytest tests for the ContextVar-based logging context + LogRecordFactory injection.
#
# Assumptions (adjust imports to your project layout):
# - commonlib.logging exposes: setup_logging, get_logger, LogConfig
# - commonlib.logging_context exposes: bind_context, clear_context, get_context, context_scope
#
# Run:
#   pytest -q

import asyncio
import logging
import threading
from pathlib import Path
from typing import Any

import pytest
from awrfo.logging.logger import LogConfig, get_logger, setup_logging
from awrfo.logging.logging_context import (
    bind_context,
    clear_context,
    context_scope,
    get_context,
)


@pytest.fixture(autouse=True)
def _fresh_root_logging(tmp_path: Path) -> None:
    """
    Ensure each test starts with a clean logging setup.
    We configure JSON to make 'extra' fields appear as LogRecord attributes,
    and we keep stdout handler only (no files needed for these tests).
    """
    setup_logging(
        LogConfig(
            level="INFO",
            json=True,
            service="test-service",
            version="0.0-test",
            log_dir=None,
        )
    )
    clear_context()


class _CaptureHandler(logging.Handler):
    """Capture LogRecords in-memory for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture()
def capture_handler() -> _CaptureHandler:
    """
    Attach a capture handler to the root logger and remove it after the test.
    """
    h = _CaptureHandler()
    root = logging.getLogger()
    root.addHandler(h)
    try:
        yield h
    finally:
        root.removeHandler(h)


def _record_field(record: logging.LogRecord, name: str) -> Any:
    """
    Get a field set via LogRecordFactory / extra injection.
    Raises AssertionError with helpful context if missing.
    """
    if not hasattr(record, name):
        raise AssertionError(f"Record missing field '{name}'. Available: {sorted(record.__dict__.keys())}")
    return getattr(record, name)


@pytest.mark.asyncio
async def test_async_tasks_do_not_override_each_other(capture_handler: _CaptureHandler) -> None:
    """
    Two concurrent async tasks must keep their own context.
    """

    log = get_logger("svc")

    async def worker(req_id: str) -> None:
        clear_context()
        bind_context({"request_id": req_id})
        # interleave tasks
        await asyncio.sleep(0.01)
        log.info("hello")
        # ensure cleanup doesn't affect other tasks
        clear_context()

    await asyncio.gather(worker("A"), worker("B"))

    # Find our 2 log records
    msgs = [r.getMessage() for r in capture_handler.records if r.name == "svc"]
    assert msgs.count("hello") == 2

    # Verify each record contains its correct request_id (no cross-talk)
    req_ids = sorted(_record_field(r, "request_id") for r in capture_handler.records if r.name == "svc")
    assert req_ids == ["A", "B"]


def test_threads_do_not_override_each_other(capture_handler: _CaptureHandler) -> None:
    """
    Two threads binding different contexts should not see each other's context.
    """

    log = get_logger("svc.thread")
    barrier = threading.Barrier(2)

    def worker(req_id: str) -> None:
        clear_context()
        bind_context({"request_id": req_id})
        barrier.wait()
        log.info("hello-thread")
        clear_context()

    t1 = threading.Thread(target=worker, args=("T1",), daemon=True)
    t2 = threading.Thread(target=worker, args=("T2",), daemon=True)
    t1.start()
    t2.start()
    t1.join(timeout=2)
    t2.join(timeout=2)

    req_ids = sorted(
        _record_field(r, "request_id")
        for r in capture_handler.records
        if r.name == "svc.thread" and r.getMessage() == "hello-thread"
    )
    assert req_ids == ["T1", "T2"]


def test_clear_context_prevents_leak_in_reused_worker(capture_handler: _CaptureHandler) -> None:
    """
    Demonstrates the lifecycle rule: if a worker is reused, you must clear context.
    This test checks that your recommended pattern (clear -> bind -> clear) works.
    """
    log = get_logger("svc.reuse")

    # Simulate request A on a reused worker thread
    clear_context()
    bind_context({"request_id": "REQ-A"})
    log.info("a")
    clear_context()

    # Simulate request B on the same worker thread
    clear_context()
    bind_context({"request_id": "REQ-B"})
    log.info("b")
    clear_context()

    records = [r for r in capture_handler.records if r.name == "svc.reuse"]
    assert [r.getMessage() for r in records] == ["a", "b"]
    assert _record_field(records[0], "request_id") == "REQ-A"
    assert _record_field(records[1], "request_id") == "REQ-B"


def test_context_scope_restores_previous_state() -> None:
    """
    context_scope must restore the prior context afterwards.
    """
    clear_context()
    bind_context({"k": "base"})
    assert get_context() == {"k": "base"}

    with context_scope({"k2": "temp"}):
        assert get_context() == {"k": "base", "k2": "temp"}

    assert get_context() == {"k": "base"}


def test_static_fields_are_injected_into_records(capture_handler: _CaptureHandler) -> None:
    """
    service/version should exist on every record (from LogRecordFactory),
    even without binding any context.
    """
    clear_context()
    log = get_logger("svc.static")
