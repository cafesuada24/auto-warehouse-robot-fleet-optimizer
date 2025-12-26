from dataclasses import dataclass

from app.application.dtos.qos_policy import QoSPolicy


@dataclass
class DomainEvent:
    topic: str
    payload: object
    time_ms: int
    policy: QoSPolicy
