from dataclasses import dataclass
from typing import Protocol

from pydantic import NonNegativeInt


@dataclass(frozen=True)
class EventRecord:
    seq: int
    topic: str
    time_ms: NonNegativeInt
    policy: int
    payload_type: str
    payload_b64: str


class EventStore(Protocol):
    def store(
        self,
        *,
        topic: str,
        time_ms: int,
        policy: int,
        payload_type: str,
        payload_bytes: bytes,
    ) -> EventRecord: ...
