from dataclasses import dataclass
from enum import Enum

from pydantic import NonNegativeInt

from app.types import IDType
from app.world.types import Position


@dataclass(frozen=True)
class CommandBase:
    id: IDType
    robot_id: IDType
    issued_at_ms: NonNegativeInt

@dataclass(frozen=True)
class AssignTaskCommand(CommandBase):
    task_id: IDType

@dataclass(frozen=True)
class MoveToCommand(CommandBase):
    pos: Position
    arrive_eps: float

@dataclass(frozen=True)
class CancelTaskCommand(CommandBase):
    task_id: IDType
