from dataclasses import dataclass, field
from time import monotonic, time

from app.types import IDType
from pydantic import NonNegativeInt

from .policy import CommandPolicy


@dataclass(frozen=True)
class CommandBase:
    id: IDType
    timestamp_ms: NonNegativeInt
    robot_id: IDType
    policy: CommandPolicy
    # issued_at_ms: NonNegativeInt = field(repr=False)
