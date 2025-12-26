from dataclasses import dataclass

from app.domain.types import Position

from .base import CommandBase


@dataclass(frozen=True)
class MoveToCommand(CommandBase):
    pos: Position
    arrive_eps: float
