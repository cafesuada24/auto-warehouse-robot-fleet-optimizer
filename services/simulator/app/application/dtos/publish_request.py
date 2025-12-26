from dataclasses import dataclass

from .qos_policy import QoSPolicy


@dataclass
class PublishRequest:
    topic: str
    payload: object
    time_ms: int
    policy: QoSPolicy
