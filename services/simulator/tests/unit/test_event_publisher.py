import threading
import time
from collections.abc import Callable
from typing import Any

import pytest
from app.application.dtos.qos_policy import QoSPolicy
from app.application.events.domain_event import DomainEvent
from app.infra.event_publisher import EventPublisher  # adjust import to your file


class DummyProto:
    def __init__(self, b: bytes) -> None:
        self._b = b
    def SerializeToString(self) -> bytes:
        return self._b


class FakeBus:
    def __init__(self, delay_s: float = 0.0) -> None:
        self.delay_s = delay_s
        self.published: list[tuple[str, bytes]] = []
        self._lock = threading.Lock()

    def subscribe(
        self,
        topic: str,
        callback: Callable[[Any], Any] | None = None,
    ) -> None:
        """Register the callback to the specified topic."""

    def start(self) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def publish_event(self, topic: str, message: bytes) -> None:
        if self.delay_s:
            time.sleep(self.delay_s)
        with self._lock:
            self.published.append((topic, message))


@pytest.fixture
def patch_convert(monkeypatch):
    # Patch the module where convert_to_proto is imported/used
    import app.infra.event_publisher as pubmod  # adjust to your publisher module path

    def _convert_to_proto(payload):
        # Encode payload deterministically for testing
        return DummyProto(repr(payload).encode("utf-8"))

    monkeypatch.setattr(pubmod, "convert_to_proto", _convert_to_proto)


def test_publisher_publishes_all_events_and_drains_queue(patch_convert):
    bus = FakeBus()
    pub = EventPublisher(bus, q_size=10)
    pub.start()

    items = [
        DomainEvent("A", payload={"i": 1}, time_ms=1, policy=QoSPolicy.BEST_EFFORT),
        DomainEvent("B", payload={"i": 2}, time_ms=2, policy=QoSPolicy.RELIABLE),
        DomainEvent("C", payload={"i": 3}, time_ms=3, policy=QoSPolicy.BEST_EFFORT),
    ]
    pub.enqueue_all(items)

    assert pub.wait_until_empty(timeout_s=2.0) is True
    pub.stop()

    topics = [t for (t, _) in bus.published]
    assert topics == ["A", "B", "C"]


def test_best_effort_drops_when_queue_full(patch_convert):
    bus = FakeBus(delay_s=0.05)  # slow publishing => queue fills
    pub = EventPublisher(bus, q_size=2)
    pub.start()

    # Enqueue more than queue can hold; BEST_EFFORT should drop silently
    items = [
        DomainEvent("ROBOT_STATE", payload=i, time_ms=i, policy=QoSPolicy.BEST_EFFORT)
        for i in range(20)
    ]
    pub.enqueue_all(items)

    # give it some time to process a few
    time.sleep(0.5)
    pub.stop()

    # Should have published some but likely < 20
    assert 0 < len(bus.published) < 20


def test_reliable_event_not_dropped_under_backpressure(patch_convert):
    bus = FakeBus(delay_s=0.05)
    pub = EventPublisher(bus, q_size=2)
    pub.start()

    # Fill with BEST_EFFORT first
    pub.enqueue_all([
        DomainEvent("ROBOT_STATE", payload="x1", time_ms=1, policy=QoSPolicy.BEST_EFFORT),
        DomainEvent("ROBOT_STATE", payload="x2", time_ms=2, policy=QoSPolicy.BEST_EFFORT),
    ])

    # Now enqueue RELIABLE; with correct implementation it must get through
    pub.enqueue_all([
        DomainEvent("TASK:COMPLETED", payload="done", time_ms=3, policy=QoSPolicy.RELIABLE),
    ])

    assert pub.wait_until_empty(timeout_s=3.0) is True
    pub.stop()

    topics = [t for (t, _) in bus.published]
    assert "TASK:COMPLETED" in topics
