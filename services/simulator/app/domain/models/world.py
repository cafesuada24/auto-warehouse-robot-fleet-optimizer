import dataclasses

from pydantic import NonNegativeInt, PositiveInt
from pydantic.dataclasses import dataclass

from app.types import IDType

from .map import Map
from .robot import Robot
from .task import Task


@dataclass
class World:
    map: Map
    robots: dict[IDType, Robot] = dataclasses.field(default_factory=dict)
    tasks: dict[IDType, Task] = dataclasses.field(default_factory=dict)
    time_ms: NonNegativeInt = 0
    tick_ms: PositiveInt = 100
