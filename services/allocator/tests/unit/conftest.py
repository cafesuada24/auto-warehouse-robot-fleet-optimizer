from typing import Final

import pytest
from app.application.ports.event_bus import EventMessage
from awrfo.types import UUID
from pydantic import NonNegativeFloat

# Constants
R1_ID: Final = UUID('00000000-0000-0000-0000-000000000001')
R2_ID: Final = UUID('00000000-0000-0000-0000-000000000002')
T1_ID: Final = UUID('00000000-0000-0000-0000-000000000101')
T2_ID: Final = UUID('00000000-0000-0000-0000-000000000102')


class FakeBus:
    """Mock implementation of the Event Bus for unit testing."""

    def __init__(self) -> None:
        self.inbox: list[EventMessage] = []
        self.published: list[tuple[str, bytes]] = []

    def push(self, topic: str, payload: bytes) -> None:
        self.inbox.append(EventMessage(topic=topic, payload=payload))

    def poll(self, timeout_s: NonNegativeFloat = 0.2) -> EventMessage | None:
        return self.inbox.pop(0) if self.inbox else None

    def publish(self, topic: str, payload: bytes) -> None:
        self.published.append((topic, payload))


@pytest.fixture
def bus() -> FakeBus:
    return FakeBus()


@pytest.fixture
def drain(bus: FakeBus):
    """Helper to process the next message in the bus."""

    def _drain(allocator):
        msg = bus.poll()
        if msg:
            allocator.on_message(topic=msg.topic, payload=msg.payload)

    return _drain
