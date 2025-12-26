from dataclasses import dataclass

from app.types import IDType
from pydantic import NonNegativeInt

from .policy import CommandPolicy


@dataclass(frozen=True)
class CommandBase:
    id: IDType
    robot_id: IDType
    issued_at_ms: NonNegativeInt
    policy: CommandPolicy
