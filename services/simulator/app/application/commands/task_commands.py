from dataclasses import dataclass

from app.types import IDType

from .base import CommandBase


@dataclass(frozen=True)
class AssignTaskCommand(CommandBase):
    task_id: IDType

@dataclass(frozen=True)
class CancelTaskCommand(CommandBase):
    task_id: IDType
