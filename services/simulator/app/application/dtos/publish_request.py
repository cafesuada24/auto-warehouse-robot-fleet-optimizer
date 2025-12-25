from dataclasses import dataclass
from enum import Enum


class PublishPolicy(Enum):
    RELIABLE = 1
    BEST_EFFORT = 2


@dataclass
class PublishRequest:
    topic: str
    payload: object
    time_ms: int
    policy: PublishPolicy
