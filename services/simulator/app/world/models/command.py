from dataclasses import dataclass
from enum import Enum

from pydantic import NonNegativeInt

from app.types import IDType
from app.world.types import Position


@dataclass(frozen=True)
class AssignTaskCommand:
    task_id: IDType
    robot_id: IDType

@dataclass(frozen=True)
class MoveToCommand:
    robot_id: IDType
    pos: Position
    arrive_eps: float

@dataclass(frozen=True)
class CancelTaskCommand:
    task_id: IDType
    robot_id: IDType

type Command = AssignTaskCommand | MoveToCommand | CancelTaskCommand
